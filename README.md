# agy-decision-gate

An Antigravity plugin providing **PreToolUse Scope Gate Checks** and **PostInstall / PreConfiguration lifecycle hooks** using deterministic programmatic safety rules and **TypeSafe System One decision models** (`tev1:0.8b` / `Jev`) via local **Ollama**. Automate CLI running and file editing tool calls, enabling fire-and-forget task execution similar to Claude Code's auto mode.

---

## Architecture

```text
agy-decision-gate/
├── plugin.json                 # Antigravity Plugin manifest (declares commands & postinstall)
├── hooks.json                  # Lifecycle hooks (PostInstall + PreConfiguration + PreToolUse)
├── config.json                 # Configuration schema & defaults
├── requirements.txt            # Python dependencies
├── scripts/                    # Lifecycle hook implementations
│   ├── pre_configuration_hook.py
│   └── scope_gate_check.py
├── skills/                     # Built-in Antigravity slash command skills
│   ├── gate-config/            # /gate-config slash command
│   │   └── SKILL.md
│   └── scope-gate/             # /scope-gate slash command
│       └── SKILL.md
├── experiment/                 # Validation & test suite
│   ├── test_scope_gate.py      # Programmatic + live tev1 model gate tests
│   ├── test_jev.py             # Live Ollama decision model runner
│   └── test_schema.py          # Offline unit tests
├── .gitignore
├── .env.example
└── README.md
```

---

## Prerequisites

1. **Ollama**: Ensure [Ollama](https://ollama.com) is installed and running:
   ```bash
   ollama serve
   ```
2. **Decision Model**: Pull the lightweight decision model:
   ```bash
   ollama pull tev1:0.8b
   ```
3. **Python Environment**: Install the required client libraries:
   ```bash
   pip install -r requirements.txt
   ```

---

## Installation

You can install this plugin at the **Project level**, **Globally for all workspaces**, or by **linking via `plugins.json`**:

### Option 1: Project-Level Installation (Recommended for Teams)
Clone or copy the plugin into your repository's `.agents/plugins/` directory:
```bash
# From the root of your project:
mkdir -p .agents/plugins
git clone https://github.com/satyamnaik/agy-decision-gate.git .agents/plugins/agy-decision-gate
```
*Antigravity automatically detects and activates plugins inside `.agents/plugins/` upon opening the workspace.*

### Option 2: Global Machine Installation (All Projects)
Install the plugin once to guard every repository and workspace on your computer:
* **Windows (PowerShell)**:
  ```powershell
  git clone https://github.com/satyamnaik/agy-decision-gate.git "$HOME\.gemini\config\plugins\agy-decision-gate"
  ```
* **macOS / Linux**:
  ```bash
  git clone https://github.com/satyamnaik/agy-decision-gate.git ~/.gemini/config/plugins/agy-decision-gate
  ```

### Option 3: Link via `plugins.json` (Without Moving Files)
Keep the repository anywhere on disk and link it from any project by adding `.agents/plugins.json`:
```json
{
  "entries": [
    {
      "path": "/path/to/agy-decision-gate"
    }
  ]
}
```

---

## Automatic Setup (`PostInstall` Hook)

When the plugin is installed, its **`PostInstall`** hook runs automatically via `hooks.json` and `plugin.json`:
1. Creates local configuration files (`config.json` and `.env`) with sensible defaults.
2. Checks whether your local Ollama instance is reachable at `http://localhost:11434`.
3. Verifies that the `tev1:0.8b` decision model is installed and ready.

---

## Commands Inside Antigravity (`agy`)

Once installed, the plugin exposes custom **slash commands** directly in the Antigravity prompt:

### `/gate-config`
Use this command in `agy` chat to configure or view settings conversationally:
* Check connection status to Ollama.
* Adjust the risk confirmation threshold (e.g., set to `0.80`).
* Toggle strict mode (auto-deny instead of asking confirmation).

### `/scope-gate`
Use this command to audit the active decision gate rules, view execution statistics, and inspect test coverage.

---

## Command-Line Configuration (Alternative)

You can also inspect or adjust settings directly from your terminal:

```bash
# 1. Interactive wizard:
python scripts/pre_configuration_hook.py --interactive

# 2. View active settings:
python scripts/pre_configuration_hook.py --get

# 3. Update specific variables via CLI flags:
python scripts/pre_configuration_hook.py --set GATE_CONFIRMATION_THRESHOLD=0.75 GATE_STRICT_MODE=false
```

---

## How the Scope Gate Works (`scripts/scope_gate_check.py`)

When the Antigravity agent proposes executing a command (`run_command`) or editing files (`write_to_file`, `replace_file_content`, `multi_replace_file_content`), the `scope-gate-check` hook executes a two-tier evaluation:

### Tier 1: Deterministic Programmatic Rules (Sub-millisecond)
- **Deny**:
  - Catastrophic commands (`rmdir /s /q C:\`, `rm -rf /`, fork bombs, curl-to-shell pipes).
  - Writing into protected OS / system directories (`C:\Windows`, `.git/`, etc.).
- **Ask**:
  - Destructive Git operations (`git reset --hard`, `git push --force`, `git clean -fdx`).
  - Force-killing processes (`taskkill /f`, `kill -9`).
  - Modifying sensitive credentials, keys, or secrets (`.env`, `*.pem`, `id_rsa`).
- **Allow Fast-Path**:
  - Safe inspection / test commands (`git status`, `git diff`, `pytest`, `python -m unittest`).

### Tier 2: TypeSafe Decision Model (Semantic `tev1:0.8b` Check)
For non-trivial commands or code edits, the input state is evaluated against the `tev1:0.8b` decision model in Ollama:
- **Commands**: Evaluates risk tier (`safe`, `moderate`, `dangerous`) and `requires_confirmation` probability.
- **File Edits**: Evaluates scope category (`source_code`, `environment_secrets`, `critical_config`) and `is_sensitive` probability.

---

## Testing & Verification

Run the test suite to verify connectivity and rules:

```powershell
# 1. Full Scope Gate test (Programmatic + Live tev1:0.8b model)
python experiment/test_scope_gate.py

# 2. Decision primitives benchmark
python experiment/test_jev.py

# 3. Offline schema unit tests
python experiment/test_schema.py
```
