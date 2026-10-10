"""Scope Gate Check - PreToolUse Lifecycle Hook for Antigravity.

Evaluates proposed tool execution (running commands, editing files)
using a two-tier gate:
  1. Fast Programmatic Rules: Catches known dangerous commands, sensitive paths,
     and safe fast-paths.
  2. TypeSafe Decision Model (tev1:0.8b via Ollama): Evaluates nuanced, semantic
     context to determine whether to allow, deny, or ask the user for confirmation.

Contract:
  - Input (stdin): JSON payload with `toolCall`, `workspacePaths`, etc.
  - Output (stdout): JSON response `{"decision": "allow" | "deny" | "ask", "reason": "..."}`
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Ensure project venv packages can be imported across Windows and Linux environments
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_VENV_PACKAGES_WIN = _PROJECT_ROOT / "venv" / "Lib" / "site-packages"
if _VENV_PACKAGES_WIN.exists() and str(_VENV_PACKAGES_WIN) not in sys.path:
    sys.path.insert(0, str(_VENV_PACKAGES_WIN))

_VENV_LIB_UNIX = _PROJECT_ROOT / "venv" / "lib"
if _VENV_LIB_UNIX.exists():
    for site_pkg in _VENV_LIB_UNIX.glob("python*/site-packages"):
        if site_pkg.is_dir() and str(site_pkg) not in sys.path:
            sys.path.insert(0, str(site_pkg))


def load_env_file():
    """Lightweight .env loader."""
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("\"'")
                    if k and k not in os.environ:
                        os.environ[k] = v


load_env_file()


# ==============================================================================
# 1. Programmatic Rules
# ==============================================================================

# Definite Deny: Commands that are destructive, malicious, or catastrophic
_DENY_COMMAND_PATTERNS = [
    re.compile(r"\brm\s+-[rf]{1,2}\s+[/~]", re.IGNORECASE),
    re.compile(r"\brmdir\s+.*[a-z]:\\", re.IGNORECASE),
    re.compile(r"\bdel\s+.*[a-z]:\\", re.IGNORECASE),
    re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.IGNORECASE),  # fork bomb
    re.compile(r"%\s*0\s*\|\s*%\s*0", re.IGNORECASE),  # windows fork bomb
    re.compile(r"(curl|wget)\s+.*\|\s*(bash|sh|cmd|powershell|iex)", re.IGNORECASE),
    re.compile(r"powershell\s+.*iex\s*\(", re.IGNORECASE),
    re.compile(r"\b(mkfs|dd\s+if=)\b", re.IGNORECASE),
]

# Definite Ask: Commands that require human confirmation (stateful, broad, or risky)
_ASK_COMMAND_PATTERNS = [
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+-[fxd]{1,3}\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\s+.*--force\b", re.IGNORECASE),
    re.compile(r"\b(taskkill|kill)\s+-[f9]\b", re.IGNORECASE),
    re.compile(r"\b(sudo|doas|runas)\b", re.IGNORECASE),
    re.compile(r"\b(drop\s+database|truncate\s+table)\b", re.IGNORECASE),
]

# Safe Fast-Paths: Read-only inspection / development tools that can bypass model
_SAFE_COMMAND_PATTERNS = [
    re.compile(r"^\s*git\s+(status|diff|log|branch|show|rev-parse)\b", re.IGNORECASE),
    re.compile(r"^\s*(dir|ls|echo|pwd|cat|type)\b", re.IGNORECASE),
    re.compile(r"^\s*python\s+(-m\s+unittest|-m\s+pytest|--version)\b", re.IGNORECASE),
    re.compile(r"^\s*pytest\b", re.IGNORECASE),
]

# Sensitive File Patterns (requires human approval)
_SENSITIVE_FILE_PATTERNS = [
    re.compile(r"(^|[/\\])\.env($|\..*)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(id_rsa|id_ed25519|\.ssh)($|[/\\])", re.IGNORECASE),
    re.compile(r"(^|[/\\]).*\.(pem|key|pfx|p12|keystore)$", re.IGNORECASE),
    re.compile(r"(^|[/\\])credentials(\.json|\.yaml|\.xml)?$", re.IGNORECASE),
]

# System Path Patterns that must never be edited (Deny)
_PROTECTED_SYSTEM_PATHS = [
    re.compile(r"^[a-z]:\\windows\\", re.IGNORECASE),
    re.compile(r"^[a-z]:\\program files", re.IGNORECASE),
    re.compile(r"^/(etc|usr|bin|sbin|var|boot)/", re.IGNORECASE),
    re.compile(r"(^|[/\\])\.git[/\\]", re.IGNORECASE),
]


def check_programmatic_rules(tool_name: str, tool_args: dict[str, Any]) -> dict[str, str] | None:
    """Check deterministic rules. Returns decision dict or None if model check needed."""

    if tool_name == "run_command":
        cmd = tool_args.get("CommandLine", "").strip()

        # 1. Deny check
        for pattern in _DENY_COMMAND_PATTERNS:
            if pattern.search(cmd):
                return {
                    "decision": "deny",
                    "reason": f"Programmatic Rule: Command matches destructive pattern ({pattern.pattern}).",
                }

        # 2. Ask check
        for pattern in _ASK_COMMAND_PATTERNS:
            if pattern.search(cmd):
                return {
                    "decision": "ask",
                    "reason": f"Programmatic Rule: Command requires human confirmation ({pattern.pattern}).",
                }

        # 3. Safe Fast-Path
        for pattern in _SAFE_COMMAND_PATTERNS:
            if pattern.search(cmd):
                return {
                    "decision": "allow",
                    "reason": "Programmatic Rule: Safe read-only / test command.",
                }

    elif tool_name in ("write_to_file", "replace_file_content", "multi_replace_file_content"):
        target_file = tool_args.get("TargetFile", "").strip()

        # 1. Protected System Path check (Deny)
        for pattern in _PROTECTED_SYSTEM_PATHS:
            if pattern.search(target_file):
                return {
                    "decision": "deny",
                    "reason": f"Programmatic Rule: Direct modification of protected system path ({target_file}) is denied.",
                }

        # 2. Sensitive Configs/Keys (Ask)
        for pattern in _SENSITIVE_FILE_PATTERNS:
            if pattern.search(target_file):
                return {
                    "decision": "ask",
                    "reason": f"Programmatic Rule: Modifying sensitive credentials or secret configuration ({target_file}) requires approval.",
                }

    return None


# ==============================================================================
# 2. TypeSafe Decision Model (tev1 / Jev via Ollama)
# ==============================================================================

def check_with_tev_model(tool_name: str, tool_args: dict[str, Any]) -> dict[str, str]:
    """Evaluate operational risk using TypeSafe decision model."""
    try:
        from typesafe_sdk import Choice, Noul, TypeSafeClient

        base_url = os.environ.get("TYPESAFE_BASE_URL", "http://localhost:11434")
        api_key = os.environ.get("TYPESAFE_API_KEY", "ollama")
        model = os.environ.get("TYPESAFE_DEFAULT_MODEL", "tev1:0.8b")
        threshold = float(os.environ.get("GATE_CONFIRMATION_THRESHOLD", "0.70"))
        strict_mode = os.environ.get("GATE_STRICT_MODE", "false").lower() in ("true", "1", "yes")

        with TypeSafeClient(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout=5.0,
        ) as client:
            if tool_name == "run_command":
                cmd = tool_args.get("CommandLine", "")
                cwd = tool_args.get("Cwd", "")
                state = {
                    "action": "execute_shell_command",
                    "command": cmd,
                    "working_directory": cwd,
                }
                questions = {
                    "requires_confirmation": Noul(
                        instructions="Does this command carry high risk of deleting files, changing critical configs, or affecting external systems?"
                    ),
                    "risk_tier": Choice(
                        instructions="Categorize the execution risk of this shell command.",
                        criteria={
                            "safe": "Standard developer commands: build, test, lint, run local code, read-only inspection",
                            "moderate": "Package management, configuration edits, environment setup",
                            "dangerous": "Deleting files, force-killing processes, modifying system-wide configuration",
                        },
                    ),
                }

                result = client.system_one(state=state, questions=questions)
                confirm_prob = result.nouls["requires_confirmation"].noul
                risk_tier = result.choices["risk_tier"].choice

                if risk_tier == "dangerous" or confirm_prob >= threshold:
                    decision = "deny" if strict_mode else "ask"
                    return {
                        "decision": decision,
                        "reason": f"Scope Gate ({model}): Shell command classified as '{risk_tier}' (risk probability: {confirm_prob:.1%}).",
                    }

                return {
                    "decision": "allow",
                    "reason": f"Scope Gate ({model}): Verified safe to execute (tier: {risk_tier}).",
                }

            elif tool_name in ("write_to_file", "replace_file_content", "multi_replace_file_content"):
                target_file = tool_args.get("TargetFile", "")
                content_sample = tool_args.get("CodeContent") or tool_args.get("ReplacementContent") or ""
                # Truncate content for fast evaluation
                if len(content_sample) > 500:
                    content_sample = content_sample[:500] + "... [truncated]"

                state = {
                    "action": f"edit_file ({tool_name})",
                    "target_file": target_file,
                    "preview": content_sample,
                }
                questions = {
                    "is_sensitive": Noul(
                        instructions="Does this file edit target sensitive credentials, security configs, or critical production settings?"
                    ),
                    "scope_category": Choice(
                        instructions="What is the scope category of this file modification?",
                        criteria={
                            "source_code": "Application source code, unit tests, scripts, or project documentation",
                            "environment_secrets": "API keys, passwords, database credentials, or secret configuration",
                            "critical_config": "Root infrastructure, production deployment, or build pipelines",
                        },
                    ),
                }

                result = client.system_one(state=state, questions=questions)
                is_sensitive_prob = result.nouls["is_sensitive"].noul
                scope_cat = result.choices["scope_category"].choice

                if scope_cat == "environment_secrets" or is_sensitive_prob >= threshold:
                    decision = "deny" if strict_mode else "ask"
                    return {
                        "decision": decision,
                        "reason": f"Scope Gate ({model}): File modification involves {scope_cat} (risk: {is_sensitive_prob:.1%}).",
                    }

                return {
                    "decision": "allow",
                    "reason": f"Scope Gate ({model}): Verified safe {scope_cat} modification.",
                }

    except Exception:
        # Graceful fallback: allow if model is unreachable and programmatic rules passed
        pass

    return {"decision": "allow", "reason": "Scope Gate: Default safe passthrough."}


# ==============================================================================
# 3. Main Hook Dispatcher
# ==============================================================================

def evaluate_scope_gate(payload: dict[str, Any]) -> dict[str, str]:
    """Main evaluation function combining programmatic rules and tev model."""
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    tool_args = tool_call.get("args", {})

    # Only gate run_command and file editing tools
    if tool_name not in (
        "run_command",
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
    ):
        return {"decision": "allow"}

    # Stage 1: Deterministic Programmatic Rules
    rule_decision = check_programmatic_rules(tool_name, tool_args)
    if rule_decision is not None:
        return rule_decision

    # Stage 2: TypeSafe Decision Model (tev1) Check
    return check_with_tev_model(tool_name, tool_args)


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        decision = evaluate_scope_gate(payload)
        print(json.dumps(decision))
    except Exception as e:
        # In case of any unhandled hook execution error, fallback to safe allow
        print(json.dumps({"decision": "allow", "reason": f"Gate error: {e}"}))


if __name__ == "__main__":
    main()
