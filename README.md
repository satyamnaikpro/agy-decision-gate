# agy-decision-gate

An Antigravity plugin providing **PreToolUse Scope Gate Checks** and **PreConfiguration lifecycle hooks** using deterministic programmatic safety rules and **TypeSafe System One decision models** (`tev1:0.8b` / `Jev`) via local **Ollama**. Automate CLI running and file editing tool calls, enabling fire-and-forget task execution similar to Claude Code's auto mode.

---

## Architecture

```text
agy-decision-gate/
├── plugin.json                 # Antigravity Plugin manifest
├── hooks.json                  # Lifecycle hooks (PreConfiguration + PreToolUse)
├── config.json                 # Configuration schema & defaults
├── requirements.txt            # Python dependencies
├── scripts/                    # Lifecycle hook implementations
│   ├── pre_configuration_hook.py
│   └── scope_gate_check.py
├── skills/                     # Plugin skills
│   └── scope-gate/
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

## Post-Installation Configuration

After installing the plugin, you can customize thresholds and connection settings using any of the following methods:

### Method 1: Interactive Setup Wizard (Fastest)
Run the built-in configuration wizard in your terminal:
```bash
python scripts/pre_configuration_hook.py --interactive
```
The wizard prompts for:
* **Ollama Server URL** (default: `http://localhost:11434`)
* **Decision Model** (default: `tev1:0.8b`)
* **API Key / Token** (default: `ollama`)
* **Confirmation Threshold** (default: `0.70` — risk probability above which the agent asks for confirmation)
* **Strict Mode** (default: `false` — if `true`, automatically denies high-risk actions instead of asking)

### Method 2: Command-Line Flags
Inspect or update settings instantly via CLI:
```bash
# View active configuration:
python scripts/pre_configuration_hook.py --get

# Adjust the human approval threshold:
python scripts/pre_configuration_hook.py --set GATE_CONFIRMATION_THRESHOLD=0.80

# Enable strict deny mode:
python scripts/pre_configuration_hook.py --set GATE_STRICT_MODE=true
```

### Method 3: Edit `.env` or `config.json`
Directly configure via `.env` in the plugin directory:
```env
TYPESAFE_BASE_URL=http://localhost:11434
TYPESAFE_DEFAULT_MODEL=tev1:0.8b
TYPESAFE_API_KEY=ollama
GATE_CONFIRMATION_THRESHOLD=0.70
GATE_STRICT_MODE=false
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
