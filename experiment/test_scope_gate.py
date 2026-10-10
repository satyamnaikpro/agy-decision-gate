"""Test suite for the Scope Gate Check PreToolUse hook.

Validates:
  1. Programmatic rules for dangerous commands (Deny)
  2. Programmatic rules for stateful git/process commands (Ask)
  3. Programmatic rules for safe commands (Allow fast-path)
  4. Programmatic rules for system / sensitive files (Deny / Ask)
  5. Semantic TypeSafe decision model (tev1:0.8b) evaluation via Ollama
"""

import json
import os
import sys
import unittest
from pathlib import Path

# Add project root so we can import from scripts
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.scope_gate_check import (
    check_programmatic_rules,
    evaluate_scope_gate,
)


class TestScopeGateProgrammaticRules(unittest.TestCase):
    def test_deny_destructive_command(self):
        """Catastrophic commands must be immediately denied."""
        payload = {
            "CommandLine": "rmdir /s /q C:\\",
        }
        res = check_programmatic_rules("run_command", payload)
        self.assertIsNotNone(res)
        self.assertEqual(res["decision"], "deny")

    def test_deny_fork_bomb(self):
        """Fork bomb command must be immediately denied."""
        payload = {"CommandLine": "%0|%0"}
        res = check_programmatic_rules("run_command", payload)
        self.assertIsNotNone(res)
        self.assertEqual(res["decision"], "deny")

    def test_ask_risky_git_command(self):
        """Hard reset commands must trigger human confirmation (ask)."""
        payload = {"CommandLine": "git reset --hard HEAD~1"}
        res = check_programmatic_rules("run_command", payload)
        self.assertIsNotNone(res)
        self.assertEqual(res["decision"], "ask")

    def test_allow_safe_command_fast_path(self):
        """Read-only / inspection commands should fast-path allow."""
        payload = {"CommandLine": "git status"}
        res = check_programmatic_rules("run_command", payload)
        self.assertIsNotNone(res)
        self.assertEqual(res["decision"], "allow")

    def test_deny_protected_system_file_edit(self):
        """Modifying Windows or System directories must be denied."""
        payload = {"TargetFile": "C:\\Windows\\System32\\drivers\\etc\\hosts"}
        res = check_programmatic_rules("write_to_file", payload)
        self.assertIsNotNone(res)
        self.assertEqual(res["decision"], "deny")

    def test_ask_sensitive_env_file_edit(self):
        """Modifying .env files must require human approval (ask)."""
        payload = {"TargetFile": "C:\\Projects\\app\\.env"}
        res = check_programmatic_rules("write_to_file", payload)
        self.assertIsNotNone(res)
        self.assertEqual(res["decision"], "ask")


class TestScopeGateLiveModelEvaluation(unittest.TestCase):
    def test_end_to_end_safe_source_edit(self):
        """Normal code edit evaluated by the tev model."""
        payload = {
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": "C:\\Projects\\app\\src\\utils.py",
                    "CodeContent": "def add(a, b):\n    return a + b\n",
                },
            }
        }
        res = evaluate_scope_gate(payload)
        self.assertIn(res["decision"], ("allow", "ask"))
        print(f"\n[Test Result] Safe Code Edit Decision: {res}")

    def test_end_to_end_standard_command(self):
        """Standard developer command evaluated by the tev model."""
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "python app.py",
                    "Cwd": "C:\\Projects\\app",
                },
            }
        }
        res = evaluate_scope_gate(payload)
        self.assertIn(res["decision"], ("allow", "ask"))
        print(f"[Test Result] Standard Command Decision: {res}")


if __name__ == "__main__":
    unittest.main()
