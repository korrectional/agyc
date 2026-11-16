import unittest
import sys
import os
import subprocess
from agyc import strip_ansi, mask_secret, scan_text_for_secrets, StreamMonitor

class TestAgyc(unittest.TestCase):
    def test_strip_ansi(self):
        colored = "\x1b[32m> 1. Yes, \x1b[0mallow"
        self.assertEqual(strip_ansi(colored), "> 1. Yes, allow")

        bold_cyan = "\x1b[1;36mHeader\x1b[0m"
        self.assertEqual(strip_ansi(bold_cyan), "Header")

        plain = "Plain text without formatting"
        self.assertEqual(strip_ansi(plain), plain)

    def test_mask_secret(self):
        self.assertEqual(mask_secret("1234"), "****")
        self.assertEqual(mask_secret("sk-proj-1234567890abcdef"), "sk-p****cdef")

    def test_scan_text_for_secrets(self):
        text = "Here is my openai key sk-proj-12345678901234567890 and AWS key AKIAIOSFODNN7EXAMPLE"
        findings = scan_text_for_secrets(text)
        types = [f[0] for f in findings]
        self.assertIn("OpenAI / LLM API Key", types)
        self.assertIn("AWS Access Key ID", types)

        clean_text = "Just a normal prompt asking to write a sorting algorithm in Python."
        self.assertEqual(scan_text_for_secrets(clean_text), [])

    def test_stream_monitor_detection(self):
        monitor = StreamMonitor(target_str="> 1. Yes, ")
        # Feed benign chunks
        self.assertFalse(monitor.feed("Running command...\n"))
        self.assertFalse(monitor.feed("Do you want to continue?\n"))

        # Feed target chunk
        self.assertTrue(monitor.feed("> 1. Yes, run this command\n"))

        # Subsequent text doesn't trigger immediately
        self.assertFalse(monitor.feed("  2. No, skip\n"))

    def test_stream_monitor_ansi_and_split(self):
        monitor = StreamMonitor(target_str="> 1. Yes, ")
        # Split across two chunks with ANSI codes
        self.assertFalse(monitor.feed("\x1b[32m> 1. "))
        self.assertTrue(monitor.feed("Yes, \x1b[0mexecute\n"))

    def test_stream_monitor_multiple_prompts(self):
        monitor = StreamMonitor(target_str="> 1. Yes, ")
        # Prompt 1
        self.assertTrue(monitor.feed("Action 1:\n> 1. Yes, proceed\n"))
        self.assertFalse(monitor.feed("Waiting for next...\n"))

        # Prompt 2
        self.assertTrue(monitor.feed("Action 2:\n> 1. Yes, proceed\n"))

    def test_end_to_end_mock_auto_enter(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        mock_path = os.path.join(script_dir, "mock_agy.py")
        agyc_path = os.path.join(script_dir, "agyc.py")

        cmd = [sys.executable, agyc_path, "--agyc-target", sys.executable, mock_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Confirmed 1! Command executed.", res.stdout)
        self.assertIn("Confirmed 2! File edited.", res.stdout)
        self.assertIn("Done!", res.stdout)

if __name__ == "__main__":
    unittest.main()
