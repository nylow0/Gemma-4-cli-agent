# Gemma CLI

A CLI tool for running Gemma 4 31B through Google AI Studio. Built as a Claude Code skill for parallelizing workflows — delegate tasks, get second opinions, run research agents in parallel.

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

# Custom persona
gemma "Review this code" --system "You are a senior code reviewer"

# Raw output (no banner, no colors — useful for piping or parallel agents)
gemma "Summarize this" --raw

# Disable agent tools for a plain LLM call
gemma "What is quantum computing?" --no-agent

# Interactive mode — just run gemma with no prompt
gemma
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

## --file vs agent mode

- **`--file`**: You explicitly pre-load files into the prompt before the call. Use when you know exactly which files are relevant and want them always included.
- **Agent mode (default)**: Gemma decides what to read, search, or browse on its own. Use for open-ended tasks, codebase exploration, or anything that needs live information.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--file` | none | File path or glob pattern to include as context (repeatable) |
| `--no-agent` | off | Disable agent tools for a plain LLM call |
| `--system` | none | System instruction / persona |
| `--temperature` | 0.7 | Generation temperature (0.0-2.0) |
| `--max-tokens` | 8192 | Max output tokens |
| `--model` | gemma-4-31b-it | Model identifier override |
| `--no-stream` | off | Disable streaming output |
| `--no-banner` | off | Hide ASCII art banner |
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

## Claude Code Skill

This repo doubles as a [Claude Code](https://claude.ai/claude-code) skill. Add it to your skills directory and Claude can delegate tasks to Gemma automatically — parallel research, second opinions, codebase exploration.

## Note

Was made with by me and my fellow claude code lmao.
