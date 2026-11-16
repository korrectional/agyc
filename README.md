# agyc - Smart Wrapper for `agy`

`agyc` is a terminal wrapper for the `agy` CLI that runs `agy` in your terminal, scans input for sensitive credentials, and automatically auto-confirms prompt dialogs (like `> 1. Yes, `).

---

## Why `agyc`?

When running `agy`, frequent tool execution and edit prompts require manual confirmation:
```
> 1. Yes, run this command
  2. No
```
`agyc` automatically handles these prompts so you do not have to press Enter each time, while also protecting you by scanning prompts for leaked API keys or private tokens.

---

## Key Features

1. **Native Interactive Terminal (TUI)**:
   - Preserves full terminal interactive support (TTY, colors, prompt formatting, arrow keys).
   - Automatically auto-approves `> 1. Yes, ` prompts.
2. **Input & Secret Scanner**:
   - Scans CLI arguments and prompts for accidental leaks of API keys, tokens, and private keys (OpenAI, Anthropic, AWS, GitHub, Google, Slack, RSA/SSH private keys).
   - Warns and asks for confirmation before sending sensitive data to `agy` (can be bypassed with `--agyc-force` / `-y` or disabled with `--agyc-no-scan`).
3. **Piped & Custom Target Support**:
   - Provides a real-time stream monitor with ANSI escape sequence stripping for piped scripts and mock testing (`--agyc-pipe`).

---

## Installation

The installer places `agyc.cmd`, `agyc.ps1`, and `agyc.py` into `C:\Users\david\AppData\Local\agy\bin` (which is already in your `PATH`):

```powershell
cd C:\Users\david\src\vectorvault\projects\agy-wrapper
.\install.ps1
```

---

## Usage

You can now run `agyc` from any terminal window:

```powershell
# Start an interactive agy session with auto-confirm enabled:
agyc

# Run with standard agy flags:
agyc -p "List recent git commits"
agyc --model "gemini-2.5-pro"
```

### Wrapper Options

All standard `agy` arguments pass straight through to `agy`. Optional wrapper flags include:

| Option | Description |
|---|---|
| `--agyc-no-auto-enter` | Disables automatic confirmation |
| `--agyc-no-scan` | Disables secret/credential scanning on input |
| `--agyc-force`, `-y` | Bypasses confirmation prompts when secrets are detected |
| `--agyc-pipe` | Forces piped stream I/O mode |
| `--agyc-verbose` | Displays diagnostic messages |
| `--agyc-target <path>` | Explicit path to target executable (default: auto-detects `agy.exe`) |
| `--agyc-help` | Shows wrapper help |

---

## Testing

Run unit and integration tests:

```powershell
python test_agyc.py
python test_passthrough.py
```
