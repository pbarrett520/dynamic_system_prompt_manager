"""
Dynamic System Prompt Manager
This script demonstrates a modular design for dynamically updating the system prompt by
injecting prompt elements based on collected conversation metrics. It is intended to
be adaptable, extensible, and asynchronous.
"""

import asyncio
import os
import time
from typing import Any, Dict, List

class MetricsCollector:
   """
   An asynchronous metrics collector.
   In a real implementation this could integrate with a sentiment analyzer, track
   conversation length, inter-message timings, or other parameters. For this example,
   it uses a dummy metric that changes over time.
   """
   def __init__(self) -> None:
       self.start_time = time.time()
       self.metrics: Dict[str, Any] = {"conversation_length": 0, "timestamp": self.start_time}

   async def collect_metrics(self) -> None:
       """Continuously update metrics asynchronously."""
       while True:
           # Simulate collecting some metrics. In a real use case, call external APIs
           # or services to get sentiment, conversation length, etc.
           current_time = time.time()
           self.metrics["timestamp"] = current_time
           # Dummy metric: conversation length increases over time (modulo for demo)
           self.metrics["conversation_length"] = int(current_time - self.start_time)
           print(f"[MetricsCollector] Collected metrics: {self.metrics}")
           await asyncio.sleep(5)  # update metrics every 5 seconds

   def get_metrics(self) -> Dict[str, Any]:
       """
       Return a copy of the latest metrics.
       Returns:
           A dictionary containing the current metrics.
       """
       return self.metrics.copy()

class PromptElementProvider:
   """
   Provides dynamic prompt elements based on configurable rules and metrics.
   The rules are stored in a configuration dictionary (could be loaded from a JSON or YAML file).
   """
   def __init__(self, config: Dict[str, Any]) -> None:
       self.config = config

   def get_prompt_elements(self, metrics: Dict[str, Any]) -> List[str]:
       """
       Determine which prompt elements to inject based on the current metrics.
       Args:
           metrics: A dictionary of conversation metrics.
       Returns:
           A list of prompt element strings.
       """
       elements: List[str] = []
       conv_length = metrics.get("conversation_length", 0)
       print(f"[PromptElementProvider] Conversation length: {conv_length}")

       if conv_length > 50:
           element = self.config.get("long_convo_addition", "")
           print("[PromptElementProvider] Using long conversation addition.")
       else:
           element = self.config.get("short_convo_addition", "")
           print("[PromptElementProvider] Using short conversation addition.")

       if element:
           elements.append(element)

       print(f"[PromptElementProvider] Final prompt elements: {elements}")
       return [el for el in elements if el]

class PromptManager:
   """
   Manages the system prompt by combining a dynamic timestamp, a dynamic config string,
   and the static base prompt from a separate file.
   Each updated prompt is written to 'system_prompt.txt' and also logged for historical record.
   """
   def __init__(
       self,
       base_prompt_file: str,
       prompt_file: str,
       provider: PromptElementProvider,
       collector: MetricsCollector
   ) -> None:
       self.base_prompt_file = base_prompt_file  # File containing the unchanging base prompt
       self.prompt_file = prompt_file            # The file to which we'll write the combined system prompt
       self.provider = provider
       self.collector = collector
       # Define a log file to store the history of prompts
       self.log_file = os.path.join(os.path.dirname(self.prompt_file), "system_prompt_log.txt")

   def load_base_prompt(self) -> str:
       """
       Reads and returns the base system prompt from the designated base prompt file.
       Returns:
           The base prompt as a string. Returns an empty string if the file cannot be read.
       """
       try:
           abs_path = os.path.abspath(self.base_prompt_file)
           print(f"[PromptManager] Loading base prompt from: {abs_path}")
           with open(self.base_prompt_file, "r", encoding="utf-8") as f:
               base_prompt = f.read()
           print(f"[PromptManager] Loaded base prompt:\n{base_prompt}")
           return base_prompt
       except Exception as e:
           print(f"[PromptManager] Error reading base prompt file: {e}")
           return ""

   def save_system_prompt(self, prompt: str) -> None:
       """
       Writes the updated system prompt to the prompt file and logs the update.
       Args:
           prompt: The complete prompt string to save.
       """
       try:
           abs_path = os.path.abspath(self.prompt_file)
           print(f"[PromptManager] Saving system prompt to: {abs_path}")
           with open(self.prompt_file, "w", encoding="utf-8") as f:
               f.write(prompt)
           print("[PromptManager] System prompt successfully saved.")
       except Exception as e:
           print(f"[PromptManager] Error writing to prompt file: {e}")

       # Append this updated prompt to a log file
       try:
           with open(self.log_file, "a", encoding="utf-8") as log:
               log.write(prompt + "\n" + "-"*80 + "\n")
           print(f"[PromptManager] Prompt logged to: {os.path.abspath(self.log_file)}")
       except Exception as e:
           print(f"[PromptManager] Error writing to log file: {e}")

   def update_prompt(self) -> None:
    """
    Reads the base prompt from a dedicated file, obtains new dynamic elements based on current metrics,
    and writes the new combined prompt to the system prompt file. The new prompt consists of:
      1. A dynamic timestamp,
      2. A dynamic string from the configuration (based on conversation metrics),
      3. The static base prompt.
    """
    print("[PromptManager] Updating prompt...")
    if not os.path.isfile(self.base_prompt_file):
         print(f"[PromptManager] ERROR: Base prompt file does not exist at {os.path.abspath(self.base_prompt_file)}")

    base_prompt = self.load_base_prompt()
    metrics = self.collector.get_metrics()
    print(f"[PromptManager] current base prompt: {base_prompt}")
    print(f"[PromptManager] Current metrics: {metrics}")

    # Create the dynamic content
    dynamic_elements = self.provider.get_prompt_elements(metrics)
    dynamic_config_string = "\n".join(dynamic_elements)

    # Create a human-readable timestamp
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(metrics.get("timestamp", time.time())))

    # Get the conversation length from the metrics instance (fixes the error)
    conversation_length = metrics["conversation_length"]

    # Build the combined variable here
    full_dynamic_prompt = (
        f"Timestamp: {current_time}\n\n"
        f"{dynamic_config_string}\n\n"
        f"Length of Conversation: {conversation_length}\n\n"
        f"{base_prompt}"
    )

    print("[PromptManager] Full dynamic prompt to be saved:")
    print(full_dynamic_prompt)

    # Save the full dynamic prompt to system_prompt.txt and log it
    self.save_system_prompt(full_dynamic_prompt)
    print("[PromptManager] Prompt updated successfully.")


   async def periodic_update(self, interval: float = 10.0) -> None:
       """
       Periodically update the system prompt every 'interval' seconds.
       Args:
           interval: Time in seconds between updates.
       """
       while True:
           self.update_prompt()
           await asyncio.sleep(interval)

async def main() -> None:
   """
   Main function to start the metrics collector and prompt manager.
   Loads a configuration for dynamic prompt elements, initializes the components, and starts
   periodic updates in the event loop.
   """
   print("[Main] Starting script execution.")
   print(f"[Main] Current working directory: {os.getcwd()}")

   # Hardcoded configuration for dynamic prompt elements
   config: Dict[str, Any] = {
       "long_convo_addition": (
           "You have engaged deeply in the discussion. Let the accumulated wisdom "
           "and weariness of a long conversation guide your next words."
       ),
       "short_convo_addition": (
           "Each new interaction brings fresh perspectives. Embrace the novelty of our exchange."
       )
   }

   # Initialize components
   metrics_collector = MetricsCollector()
   prompt_provider = PromptElementProvider(config)
   
   # Define the static base prompt file and the dynamic system prompt file.
   base_prompt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_system_prompt.txt")
   system_prompt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_prompt.txt")

   prompt_manager = PromptManager(
       base_prompt_file=base_prompt_file,
       prompt_file=system_prompt_file,
       provider=prompt_provider,
       collector=metrics_collector
   )

   # Start collecting metrics asynchronously in the background.
   asyncio.create_task(metrics_collector.collect_metrics())
   
   # Periodically update the prompt every 10 seconds.
   await prompt_manager.periodic_update(interval=10.0)

if __name__ == "__main__":
   asyncio.run(main())
