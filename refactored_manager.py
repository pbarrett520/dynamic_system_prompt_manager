from __future__ import annotations
import asyncio
import contextlib  # <-- NEW
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="[%(levelname)s] %(message)s")


class MetricsCollector:
    """Asynchronously produces a *rolling* metrics snapshot."""

    _SAMPLE_PERIOD = 5  # seconds

    def __init__(self) -> None:
        self._start = time.time()
        self._latest: Dict[str, Any] = {
            "conversation_length": 0,
            "timestamp": self._start,
        }
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None

    @property
    def latest(self) -> Dict[str, Any]:
        return self._latest.copy()

    async def _tick(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._SAMPLE_PERIOD)
                async with self._lock:
                    now = time.time()
                    self._latest.update(
                        timestamp=now,
                        conversation_length=int(now - self._start),
                    )
                logger.debug("metrics=%s", self._latest)
        except asyncio.CancelledError:
            logger.info("MetricsCollector stopped.")
            raise

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._tick(), name="metrics_collector")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task


@dataclass(frozen=True, slots=True)
class PromptConfig:
    long_convo_addition: str
    short_convo_addition: str


class PromptElementProvider:
    def __init__(self, cfg: PromptConfig) -> None:
        self.cfg = cfg

    def get_prompt_elements(self, metrics: Dict[str, Any]) -> List[str]:
        length = metrics.get("conversation_length", 0)
        element = (
            self.cfg.long_convo_addition
            if length > 50
            else self.cfg.short_convo_addition
        )
        logger.debug("chosen_element='%s' length=%s", element, length)
        return [element] if element else []


class PromptManager:
    def __init__(
        self,
        base_prompt_path: Path,
        output_path: Path,
        provider: PromptElementProvider,
        collector: MetricsCollector,
    ) -> None:
        self.base_path = base_prompt_path
        self.out_path = output_path
        self.log_path = output_path.with_name("system_prompt_log.txt")
        self.provider = provider
        self.collector = collector
        self._cached_base: str = ""
        self._cached_mtime: float | None = None

    def _read_base_prompt(self) -> str:
        if not self.base_path.exists():
            logger.error("Base prompt does not exist: %s", self.base_path)
            return ""
        mtime = self.base_path.stat().st_mtime
        if mtime != self._cached_mtime:
            self._cached_base = self.base_path.read_text(encoding="utf-8")
            self._cached_mtime = mtime
            logger.debug("Base prompt reloaded (%s bytes)", len(self._cached_base))
        return self._cached_base

    def _build_prompt(self) -> str:
        metrics = self.collector.latest
        dynamic = "\n".join(self.provider.get_prompt_elements(metrics))
        timestamp = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(metrics["timestamp"])
        )
        return (
            f"Timestamp: {timestamp}\n\n"
            f"{dynamic}\n\n"
            f"Length of Conversation: {metrics['conversation_length']}\n\n"
            f"{self._read_base_prompt()}"
        )

    def write_prompt(self) -> None:
        prompt_txt = self._build_prompt()
        self.out_path.write_text(prompt_txt, encoding="utf-8")
        # --- append mode fix
        with self.log_path.open("a", encoding="utf-8") as log:
            log.write(prompt_txt + "\n" + "-" * 80 + "\n")
        logger.info("Prompt updated → %s", self.out_path)

    async def periodic_update(self, interval: float = 10.0) -> None:
        try:
            while True:
                self.write_prompt()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("PromptManager stopped.")
            raise


async def _main() -> None:
    root = Path(__file__).resolve().parent
    cfg = PromptConfig(
        long_convo_addition=(
            "You have engaged deeply in the discussion. Let the accumulated wisdom "
            "and weariness of a long conversation guide your next words."
        ),
        short_convo_addition=(
            "Each new interaction brings fresh perspectives. Embrace the novelty of our exchange."
        ),
    )

    collector = MetricsCollector()
    collector.start()
    provider = PromptElementProvider(cfg)
    mgr = PromptManager(
        base_prompt_path=root / "base_system_prompt.txt",
        output_path=root / "system_prompt.txt",
        provider=provider,
        collector=collector,
    )

    updater = asyncio.create_task(mgr.periodic_update(10.0), name="prompt_updater")
    try:
        await updater
    finally:
        await collector.stop()


if __name__ == "__main__":
    asyncio.run(_main())
