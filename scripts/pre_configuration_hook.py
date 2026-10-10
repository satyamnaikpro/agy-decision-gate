"""PreConfiguration Hook for Antigravity agy-jev-gate Plugin.

Collects, validates, and stores configuration variables from users:
  - TYPESAFE_BASE_URL: Ollama server endpoint (default: http://localhost:11434)
  - TYPESAFE_DEFAULT_MODEL: Decision model identifier (default: tev1:0.8b)
  - TYPESAFE_API_KEY: Authentication token (default: ollama)
  - GATE_CONFIRMATION_THRESHOLD: Probability threshold to trigger human confirmation (default: 0.70)
  - GATE_STRICT_MODE: Deny instead of asking on high risk (default: false)

Can be invoked:
  1. Via Antigravity PreConfiguration hook lifecycle event (JSON via stdin/stdout)
  2. Interactively in terminal (`python scripts/pre_configuration_hook.py --interactive`)
  3. Programmatically with key-value CLI flags (`python scripts/pre_configuration_hook.py --set KEY=VAL`)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
_CONFIG_JSON = _PROJECT_ROOT / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "TYPESAFE_BASE_URL": "http://localhost:11434",
    "TYPESAFE_DEFAULT_MODEL": "tev1:0.8b",
    "TYPESAFE_API_KEY": "ollama",
    "GATE_CONFIRMATION_THRESHOLD": 0.70,
    "GATE_STRICT_MODE": False,
}


def load_current_config() -> dict[str, Any]:
    """Load configuration from config.json, .env, or defaults."""
    config = dict(DEFAULT_CONFIG)

    # 1. Read config.json if exists
    if _CONFIG_JSON.exists():
        try:
            with open(_CONFIG_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    config.update(data)
        except Exception:
            pass

    # 2. Read .env file if exists
    if _ENV_FILE.exists():
        try:
            with open(_ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("\"'")
                        if k in config:
                            if isinstance(DEFAULT_CONFIG[k], float):
                                try:
                                    config[k] = float(v)
                                except ValueError:
                                    pass
                            elif isinstance(DEFAULT_CONFIG[k], bool):
                                config[k] = v.lower() in ("true", "1", "yes")
                            else:
                                config[k] = v
        except Exception:
            pass

    return config


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to both config.json and .env file."""
    # Write config.json
    with open(_CONFIG_JSON, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    # Write .env file
    env_lines = [
        "# Antigravity TypeSafe Scope Gate Configuration",
        f"TYPESAFE_BASE_URL={config.get('TYPESAFE_BASE_URL', DEFAULT_CONFIG['TYPESAFE_BASE_URL'])}",
        f"TYPESAFE_DEFAULT_MODEL={config.get('TYPESAFE_DEFAULT_MODEL', DEFAULT_CONFIG['TYPESAFE_DEFAULT_MODEL'])}",
        f"TYPESAFE_API_KEY={config.get('TYPESAFE_API_KEY', DEFAULT_CONFIG['TYPESAFE_API_KEY'])}",
        f"GATE_CONFIRMATION_THRESHOLD={config.get('GATE_CONFIRMATION_THRESHOLD', DEFAULT_CONFIG['GATE_CONFIRMATION_THRESHOLD'])}",
        f"GATE_STRICT_MODE={str(config.get('GATE_STRICT_MODE', False)).lower()}",
        "",
    ]
    with open(_ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(env_lines))


def test_ollama_connection(base_url: str, model_name: str) -> dict[str, Any]:
    """Test connectivity to Ollama and check if the model is installed."""
    try:
        import httpx2

        res = httpx2.get(f"{base_url.rstrip('/')}/api/tags", timeout=3.0)
        if res.status_code == 200:
            models = [m.get("name") for m in res.json().get("models", [])]
            installed = any(m == model_name or m.startswith(model_name.split(":")[0]) for m in models)
            return {
                "connected": True,
                "installed_models": models,
                "model_ready": installed,
            }
    except Exception as e:
        return {"connected": False, "error": str(e), "model_ready": False}

    return {"connected": False, "model_ready": False}


def interactive_prompt() -> dict[str, Any]:
    """Prompt the user interactively in a terminal for configuration variables."""
    current = load_current_config()
    print("=" * 60)
    print("Antigravity Plugin PreConfiguration Setup (agy-jev-gate)")
    print("=" * 60)

    # 1. Base URL
    default_url = current["TYPESAFE_BASE_URL"]
    val = input(f"Ollama Server URL [{default_url}]: ").strip()
    base_url = val if val else default_url

    # 2. Model Name
    default_model = current["TYPESAFE_DEFAULT_MODEL"]
    val = input(f"Decision Model Name [{default_model}]: ").strip()
    model_name = val if val else default_model

    # 3. API Key
    default_key = current["TYPESAFE_API_KEY"]
    val = input(f"API Key / Token [{default_key}]: ").strip()
    api_key = val if val else default_key

    # 4. Confirmation Threshold
    default_thresh = current["GATE_CONFIRMATION_THRESHOLD"]
    val = input(f"Risk Confirmation Threshold (0.0 - 1.0) [{default_thresh}]: ").strip()
    try:
        threshold = float(val) if val else default_thresh
    except ValueError:
        threshold = default_thresh

    # 5. Strict Mode
    default_strict = current["GATE_STRICT_MODE"]
    val = input(f"Strict Mode (Deny instead of Ask) (y/N) [{'y' if default_strict else 'n'}]: ").strip().lower()
    strict_mode = val in ("y", "yes", "true") if val else default_strict

    config = {
        "TYPESAFE_BASE_URL": base_url,
        "TYPESAFE_DEFAULT_MODEL": model_name,
        "TYPESAFE_API_KEY": api_key,
        "GATE_CONFIRMATION_THRESHOLD": threshold,
        "GATE_STRICT_MODE": strict_mode,
    }

    save_config(config)
    print("\n[Configuration Saved]")
    print(f"  Saved to: {_ENV_FILE}")
    print(f"  Saved to: {_CONFIG_JSON}")

    # Check connection
    check = test_ollama_connection(base_url, model_name)
    if check["connected"]:
        print(f"[OK] Ollama reachable at {base_url}")
        if check["model_ready"]:
            print(f"[OK] Model '{model_name}' is verified and ready to run decisions.")
        else:
            print(f"[NOTE] Model '{model_name}' not found in `ollama list`. Run `ollama pull {model_name}`.")
    else:
        print(f"[WARN] Could not reach Ollama: {check.get('error')}")

    return config


def handle_hook_execution(raw_stdin: str) -> dict[str, Any]:
    """Handle execution when invoked by Antigravity as a PreConfiguration hook."""
    current = load_current_config()
    payload = {}

    if raw_stdin.strip():
        try:
            payload = json.loads(raw_stdin)
        except Exception:
            pass

    # Extract any configuration passed in payload
    incoming_vars = payload.get("configuration") or payload.get("config") or payload.get("variables") or {}
    if isinstance(incoming_vars, dict) and incoming_vars:
        for k, v in incoming_vars.items():
            if k in DEFAULT_CONFIG:
                if isinstance(DEFAULT_CONFIG[k], float):
                    try:
                        current[k] = float(v)
                    except ValueError:
                        pass
                elif isinstance(DEFAULT_CONFIG[k], bool):
                    current[k] = bool(v)
                else:
                    current[k] = str(v)
        save_config(current)

    # Test status of configured model
    status = test_ollama_connection(
        current["TYPESAFE_BASE_URL"],
        current["TYPESAFE_DEFAULT_MODEL"],
    )

    return {
        "status": "configured",
        "decision": "allow",
        "configuration": current,
        "ollama_status": status,
        "message": f"PreConfiguration ready for model '{current['TYPESAFE_DEFAULT_MODEL']}'.",
    }


def main():
    parser = argparse.ArgumentParser(description="PreConfiguration hook for agy-jev-gate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Prompt user interactively")
    parser.add_argument("--get", action="store_true", help="Print current configuration as JSON")
    parser.add_argument("--set", nargs="+", metavar="KEY=VALUE", help="Set configuration variables")
    args = parser.parse_args()

    if args.interactive:
        interactive_prompt()
        return

    if args.get:
        print(json.dumps(load_current_config(), indent=2))
        return

    if args.set:
        config = load_current_config()
        for item in args.set:
            if "=" in item:
                k, v = item.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k in config:
                    if isinstance(DEFAULT_CONFIG[k], float):
                        config[k] = float(v)
                    elif isinstance(DEFAULT_CONFIG[k], bool):
                        config[k] = v.lower() in ("true", "1", "yes")
                    else:
                        config[k] = v
        save_config(config)
        print(json.dumps({"status": "updated", "config": config}))
        return

    # Check if stdin has data (hook invocation) or is a TTY
    if sys.stdin.isatty():
        # Running directly in terminal without flags
        interactive_prompt()
    else:
        # Piped stdin from Antigravity lifecycle hook runner
        raw_stdin = sys.stdin.read()
        response = handle_hook_execution(raw_stdin)
        print(json.dumps(response))


if __name__ == "__main__":
    main()
