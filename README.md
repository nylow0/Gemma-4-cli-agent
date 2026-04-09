# Gemma CLI

A lightweight CLI tool for running Gemma 4 31B through Google AI Studio. I built it as a Claude Code skill for parallelizing workflows — delegate tasks, etc.

Supports reading files and glob patterns directly as context, so Gemma can reason over your codebase without manual copy-pasting. Also has an agent mode where Gemma can autonomously browse and read files from your file system. Also the free tier api of this model is pretty generous, so it's useful af since I'm a broke student lol.

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

1. Clone and install:

```bash
git clone https://github.com/nylow0/Gemma-4-cli-agent.git
cd Gemma-4-cli-agent
pip install -e .
```

2. Set your API key (get one at [aistudio.google.com](https://aistudio.google.com)):

```bash
# Windows (permanent)
setx GOOGLE_AI_STUDIO_KEY your-key-here

# Bash
export GOOGLE_AI_STUDIO_KEY=your-key-here
```

That's it. `gemma` is now available as a command.

## Usage

```bash
# Basic prompt
gemma "What is quantum computing?"

# Pre-load files as context
gemma "Review this code for bugs" --file src/main.py

# Multiple files and glob patterns
gemma "Explain how these modules interact" --file src/auth.py --file "src/utils/*.py"

# Agent mode — Gemma autonomously browses and reads your files
gemma "Find the main entry point and review it for issues" --agent

# Agent mode with a persona
gemma "Review the project structure and suggest improvements" --agent --system "You are a senior architect"

# Custom persona
gemma "Review this code" --system "You are a senior code reviewer"

# Raw output (no banner, no colors — useful for piping)
gemma "Summarize this" --raw
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--file` | none | File path or glob pattern to include as context (repeatable) |
| `--agent` | off | Enable file system tools — Gemma can autonomously read files, list dirs, search |
| `--system` | none | System instruction / persona |
| `--temperature` | 0.7 | Generation temperature (0.0-2.0) |
| `--max-tokens` | 8192 | Max output tokens |
| `--model` | gemma-4-31b-it | Model identifier override |
| `--no-stream` | off | Disable streaming output |
| `--no-banner` | off | Hide ASCII art banner |
| `--raw` | off | Raw output, no formatting (for piping) |

## --file vs --agent

- **`--file`**: Pre-loads specific files into the prompt. You pick which files Gemma sees.
- **`--agent`**: Gives Gemma read-only file system tools (`read_file`, `list_directory`, `search_files`). Gemma decides what to read. Use when you don't know which files matter or Gemma needs to explore.

## Claude Code Skill

This repo doubles as a [Claude Code](https://claude.ai/claude-code) skill. Add it to your skills directory and Claude can delegate tasks to Gemma automatically.

## Note

Was made with by me and my fellow claude code lmao.
