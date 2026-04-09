# Gemma CLI

A lightweight CLI tool for running Gemma 4 31B through Google AI Studio. I built it as a Claude Code skill for parallelizing workflows — delegate tasks, etc.

Supports reading files and glob patterns directly as context, so Gemma can reason over your codebase without manual copy-pasting. Also the api of this is pretty generous, so it's good since I'm a broke student lol.

```
╔════════════════════════════════════════════════════╗
║                                                    ║
║   ██████╗ ███████╗███╗   ███╗███╗   ███╗ █████╗    ║
║  ██╔════╝ ██╔════╝████╗ ████║████╗ ████║██╔══██╗   ║
║  ██║  ███╗█████╗  ██╔████╔██║██╔████╔██║███████║   ║
║  ██║   ██║██╔══╝  ██║╚██╔╝██║██║╚██╔╝██║██╔══██║   ║
║  ╚██████╔╝███████╗██║ ╚═╝ ██║██║ ╚═╝ ██║██║  ██║   ║
║   ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ║
║                                                    ║
╚════════════════════════════════════════════════════╝
```

## Setup

1. Install the dependency:

```bash
pip install google-genai
```

2. Set your API key (get one at [aistudio.google.com](https://aistudio.google.com)):

```bash
# Windows (permanent)
setx GOOGLE_AI_STUDIO_KEY your-key-here

# Bash
export GOOGLE_AI_STUDIO_KEY=your-key-here
```

3. Make `gemma` available as a command:

**Windows (CMD/PowerShell):** Create `gemma.bat` in a directory on your PATH:

```bat
@echo off
python "C:\path\to\gemma-skill\src\gemma.py" %*
```

**Bash/macOS/Linux:** Symlink or alias:

```bash
ln -s /path/to/gemma-skill/src/gemma.py ~/.local/bin/gemma
chmod +x /path/to/gemma-skill/src/gemma.py
```

## Usage

```bash
gemma "What is quantum computing?"
gemma "Review this code for bugs" --file src/main.py --raw
gemma "Explain how these modules interact" --file src/auth.py --file "src/utils/*.py" --raw
gemma "Review this code" --system "You are a senior code reviewer" --temperature 0.3
gemma "Summarize this" --max-tokens 1024 --no-banner
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--file` | none | File path or glob pattern to include as context (repeatable) |
| `--system` | none | System instruction |
| `--temperature` | 0.7 | Generation temperature (0.0–2.0) |
| `--max-tokens` | 8192 | Max output tokens |
| `--model` | gemma-4-31b-it | Model identifier override |
| `--no-stream` | off | Disable streaming output |
| `--no-banner` | off | Hide ASCII art banner |
| `--raw` | off | Raw output, no formatting (for piping) |

## Claude Code Skill

This repo doubles as a [Claude Code](https://claude.ai/claude-code) skill. Add it to your skills directory and Claude can delegate tasks to Gemma automatically.

## Note

Was made with claude code.