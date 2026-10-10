# agy-decision-gate

An Antigravity plugin providing **PreToolUse Scope Gate Checks** and **PreConfiguration lifecycle hooks** using deterministic programmatic safety rules and **TypeSafe System One decision models** (`tev1:0.8b` / `Jev`) via local **Ollama**.

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

## Two-Tier Scope Gate (`scripts/scope_gate_check.py`)

When the Antigravity agent proposes executing a command (`run_command`) or editing files (`write_to_file`, `replace_file_content`, `multi_replace_file_content`), the `scope-gate-check` hook executes:

### Tier 1: Deterministic Programmatic Rules (Instant)
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

## Configuration

Settings can be managed interactively, via `.env`, or through `config.json`:

```env
TYPESAFE_BASE_URL=http://localhost:11434
TYPESAFE_DEFAULT_MODEL=tev1:0.8b
TYPESAFE_API_KEY=ollama
GATE_CONFIRMATION_THRESHOLD=0.70
GATE_STRICT_MODE=false
```

### Interactive PreConfiguration Hook
Run:
```powershell
python scripts/pre_configuration_hook.py --interactive
```

---

## Testing & Validation

### Scope Gate Test (Programmatic Rules + Live `tev1:0.8b`)
```powershell
python experiment/test_scope_gate.py
```

### TypeSafe Primitives Live Evaluation
```powershell
python experiment/test_jev.py
```

### Offline Schema Tests
```powershell
python experiment/test_schema.py
```
