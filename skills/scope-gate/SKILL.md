---
name: scope-gate
description: Guidelines and tools for configuring and managing the TypeSafe decision gate (tev1:0.8b) that monitors shell commands and file edits.
---

# Scope Gate Skill

This skill explains how the `agy-jev-gate` plugin monitors and validates tool actions in Antigravity using **TypeSafe System One decision models** (`tev1:0.8b` / `Jev`) via local Ollama.

## Quick Management Commands

- **Check Current Configuration**:
  ```bash
  python ./scripts/pre_configuration_hook.py --get
  ```

- **Update Confirmation Threshold**:
  ```bash
  python ./scripts/pre_configuration_hook.py --set GATE_CONFIRMATION_THRESHOLD=0.75
  ```

- **Enable Strict Deny Mode**:
  ```bash
  python ./scripts/pre_configuration_hook.py --set GATE_STRICT_MODE=true
  ```

## How the Gate Works

1. **PreToolUse Interception**: Catches `run_command`, `write_to_file`, `replace_file_content`, and `multi_replace_file_content`.
2. **Programmatic Tier**: Instantly filters catastrophic commands and protected system paths.
3. **Model Tier**: Prompts `tev1:0.8b` on Ollama for semantic risk classification.
