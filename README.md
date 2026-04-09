# Gemma CLI

So I created this thing to use multiple instances of Gemma 4 model in parallel for better optimization of my workflow. Since my hardware ain't that good, have to use a google api, which is luckily pretty generous for my purposes.

The inintial idea for this was to create a cli which can be called from claude code to have multiple cheap and effective subagents to work in parallel, so I also added a skill for it lol.

### Little note

This one was mostly written via claude code.

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
gemma "Review this code" --system "You are a senior code reviewer" --temperature 0.3
gemma "Summarize this" --max-tokens 1024 --no-banner
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--system` | none | System instruction |
| `--temperature` | 0.7 | Generation temperature (0.0–2.0) |
| `--max-tokens` | 8192 | Max output tokens |
| `--model` | gemma-4-31b-it | Model identifier override |
| `--no-stream` | off | Disable streaming output |
| `--no-banner` | off | Hide ASCII art banner |
| `--raw` | off | Raw output, no formatting (for piping) |

## Claude Code Skill

Like I said in the description, this repo doubles as a [Claude Code](https://claude.ai/claude-code) skill. Add it to your skills directory and Claude can delegate tasks to Gemma automatically.