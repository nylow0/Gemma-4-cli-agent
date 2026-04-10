# Gemma CLI

A CLI tool for running Gemma 4 31B through Google AI Studio, plus two Claude Code skills that let Claude delegate tasks to Gemma automatically.

Agent mode is on by default: Gemma can browse your file system, fetch URLs, and search Google without any extra flags. The free tier API is generous af, so it's useful af since I'm a broke student lol.

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
# Basic prompt — agent mode is on by default
gemma "What's the latest news on Rust async?"

# Ask about your codebase — Gemma will read files on its own
gemma "Find the main entry point and review it for issues"

# Pre-load specific files as context
gemma "Review this code for bugs" --file src/main.py

# Multiple files and glob patterns
gemma "Explain how these modules interact" --file src/auth.py --file "src/utils/*.py"

# Multimodal — pass images, video, audio, or PDFs
gemma "Describe this image" --file photo.jpg
gemma "Transcribe this audio" --file recording.mp3
gemma "Summarize this document" --file report.pdf

# Custom persona
gemma "Review this code" --system "You are a senior code reviewer"

# Raw output (no banner, no colors — useful for piping or parallel agents)
gemma "Summarize this" --raw

# Disable agent tools for a plain LLM call
gemma "What is quantum computing?" --no-agent

# Hide thinking blocks
gemma "Explain recursion" --no-think

# Interactive mode — just run gemma with no prompt
gemma
```

## Thinking Display

When Gemma uses chain-of-thought reasoning, the thinking process is rendered in a clean bordered box — separate from the actual answer:

```
 💭 Thinking ────────────────────────────────────────
 │ Let me analyze the code structure...
 │ I see there are three main modules...
 │ The entry point is in main.py...
 ────────────────────────────────────────────────────

Here is my analysis of your code:
1. The main entry point is well-structured...
```

Toggle thinking visibility with `--no-think` or `/think` in interactive mode.

## Slash Commands

Slash commands work both in interactive mode and from the CLI:

```bash
# From the command line
gemma /help
gemma /model

# Inside interactive mode
/help              Show available commands
/clear             Clear conversation history
/model [name]      Show or change the model
/system [text]     Show or set system instruction
/file <path>       Attach a file to the next message
/files             Show attached files
/agent             Toggle agent mode (tools)
/think             Toggle thinking display
/temp <value>      Set temperature (0.0–2.0)
/exit              Exit interactive mode
```

### Attaching files mid-conversation

In interactive mode, use `/file` to attach files before your next message:

```
 ❯ /file screenshot.png
 📎 Attached: screenshot.png

 ❯ What's wrong with this UI?
 💭 Thinking ────────────────────────────────────────
 │ Looking at the screenshot...
 ────────────────────────────────────────────────────
 I can see a few issues with the layout...
```

## Agent Tools (on by default)

Gemma has read-only access to your file system, the web, and Google Search out of the box. No flag needed.

| Tool | What it does |
|------|-------------|
| `read_file` | Read any file by path |
| `list_directory` | List files and subdirectories |
| `search_files` | Find files by glob pattern |
| `grep_files` | Search file contents by regex |
| `fetch_url` | Fetch a webpage and return its text |
| `google_search` | Search Google (built-in, server-side) |

Use `--no-agent` to disable all tools and make a plain LLM call.

## Multimodal Support

Gemma 4 is natively multimodal. Pass media files with `--file` or `/file`:

| Type | Extensions |
|------|-----------|
| Images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp` |
| Video | `.mp4`, `.mov`, `.avi`, `.webm` |
| Audio | `.mp3`, `.wav`, `.ogg`, `.flac`, `.m4a` |
| Documents | `.pdf` |

Files under 20MB are sent inline. Larger files are uploaded via the Files API.

## --file vs agent mode

- **`--file`**: You explicitly pre-load files into the prompt before the call. Use when you know exactly which files are relevant and want them always included.
- **Agent mode (default)**: Gemma decides what to read, search, or browse on its own. Use for open-ended tasks, codebase exploration, or anything that needs live information.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--file` | none | File path or glob to include as context (repeatable) |
| `--no-agent` | off | Disable agent tools for a plain LLM call |
| `--system` | none | System instruction / persona |
| `--temperature` | 0.7 | Generation temperature (0.0-2.0) |
| `--max-tokens` | 8192 | Max output tokens |
| `--model` | gemma-4-31b-it | Model identifier override |
| `--no-stream` | off | Disable streaming output |
| `--no-banner` | off | Hide ASCII art banner |
| `--no-think` | off | Hide thinking blocks |
| `--raw` | off | Raw output, no formatting (for piping) |

## Running parallel agents

For true parallelism, launch multiple agents as background jobs in a single shell command:

```bash
gemma "Research topic A" --raw > /tmp/agent1.txt 2>&1 &
gemma "Research topic B" --raw > /tmp/agent2.txt 2>&1 &
gemma "Research topic C" --raw > /tmp/agent3.txt 2>&1 &
wait
cat /tmp/agent1.txt /tmp/agent2.txt /tmp/agent3.txt
```

The free tier allows 15 requests/minute, so running 3–5 agents in parallel works fine.

## Claude Code Skills

The `skills/` folder contains two [Claude Code](https://claude.ai/claude-code) skills. Install them by symlinking into `~/.claude/skills/`:

```bash
ln -s "$(pwd)/skills/gemma" ~/.claude/skills/gemma
ln -s "$(pwd)/skills/gemma-research" ~/.claude/skills/gemma-research
```

### `gemma` — Single-agent delegation

Claude delegates tasks to a single Gemma agent. Use for: second opinions on code, quick research, brainstorming, offloading subtasks.

### `gemma-research` — Multi-agent research orchestration

Implements fan-out/fan-in and stochastic consensus patterns. Claude fans out N agents (batched in groups of 5) with diverse cognitive lenses — different personas, methodologies, and perspectives — then synthesizes their outputs into a structured report.

Four research modes, auto-detected from your query:
- **explore** — brainstorming and idea generation, maximizes divergence, surfaces outliers
- **consensus** — finds the best answer by ranking claims by independent agreement
- **deep** — comprehensive coverage by assigning each agent a different PESTEL facet
- **compare** — structured pros/cons with adversarial cross-checking between options

## Note

Was made with by me and my fellow claude code lmao.
