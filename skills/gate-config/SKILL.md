---
name: gate-config
description: Configure the agy-decision-gate plugin settings, Ollama model, and risk thresholds. Triggered via /gate-config slash command or when the user wants to adjust gate parameters.
---

# Gate Configuration (/gate-config)

Use this skill when the user runs `/gate-config` or asks to configure the Scope Gate settings.

## Workflow

1. **Check Current Status**:
   Run the inspect command to see active settings and Ollama connectivity:
   ```bash
   python ./scripts/pre_configuration_hook.py --get
   ```

2. **Interactive Configuration**:
   If the user wants to adjust settings, ask them for their preferences or run:
   ```bash
   python ./scripts/pre_configuration_hook.py --set GATE_CONFIRMATION_THRESHOLD=<threshold> GATE_STRICT_MODE=<bool>
   ```

   Key parameters:
   - `TYPESAFE_BASE_URL`: Ollama endpoint (default: `http://localhost:11434`)
   - `TYPESAFE_DEFAULT_MODEL`: Decision model (default: `tev1:0.8b`)
   - `GATE_CONFIRMATION_THRESHOLD`: Human approval threshold between `0.0` and `1.0` (default: `0.70`)
   - `GATE_STRICT_MODE`: `true` to block immediately on high risk, `false` to ask confirmation

3. **Verify Decision Model**:
   Verify that Ollama responds with the model ready:
   ```bash
   python ./scripts/pre_configuration_hook.py
   ```
