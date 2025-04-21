import unittest
from unittest.mock import mock_open, patch
from typing import Dict, Any
from system_prompt_manager.manager import (
   MetricsCollector,
   PromptElementProvider,
   PromptManager,
)

class TestMetricsCollector(unittest.TestCase):
   def test_initial_metrics(self):
       collector = MetricsCollector()
       metrics = collector.get_metrics()
       self.assertIn("conversation_length", metrics)
       self.assertIsInstance(metrics["conversation_length"], int)

class TestPromptElementProvider(unittest.TestCase):
   def setUp(self):
       self.config = {
           "long_convo_addition": "This is a long conversation response.",
           "short_convo_addition": "This is a short conversation response.",
       }
       self.provider = PromptElementProvider(config=self.config)
   def test_short_convo_prompt(self):
       metrics = {"conversation_length": 20}
       result = self.provider.get_prompt_elements(metrics)
       self.assertIn(self.config["short_convo_addition"], result)
   def test_long_convo_prompt(self):
       metrics = {"conversation_length": 80}
       result = self.provider.get_prompt_elements(metrics)
       self.assertIn(self.config["long_convo_addition"], result)

class TestPromptManager(unittest.TestCase):
   def setUp(self):
       self.collector = MetricsCollector()
       self.collector.metrics = {"conversation_length": 30}
       self.config = {
           "short_convo_addition": "Short prompt addon.",
           "long_convo_addition": "Long prompt addon.",
       }
       self.provider = PromptElementProvider(config=self.config)
   @patch("builtins.open", new_callable=mock_open, read_data="Base prompt.")
   def test_load_base_prompt(self, mock_file):
       manager = PromptManager("dummy.txt", self.provider, self.collector)
       result = manager.load_base_prompt()
       self.assertEqual(result, "Base prompt.")
   @patch("builtins.open", new_callable=mock_open)
   def test_save_system_prompt(self, mock_file):
       manager = PromptManager("dummy.txt", self.provider, self.collector)
       manager.save_system_prompt("Updated prompt.")
       mock_file().write.assert_called_with("Updated prompt.")
   @patch("builtins.open", new_callable=mock_open, read_data="Base prompt.")
   def test_update_prompt(self, mock_file):
       manager = PromptManager("dummy.txt", self.provider, self.collector)
       manager.update_prompt()
       handle = mock_file()
       written_data = handle.write.call_args[0][0]
       self.assertIn("Base prompt.", written_data)
       self.assertIn("Short prompt addon.", written_data)

if __name__ == "__main__":
   unittest.main()