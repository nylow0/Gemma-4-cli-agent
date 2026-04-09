---
name: gemma
description: This skill should be used when Claude needs to delegate a task to Gemma 4 31B, run parallel research, get a second opinion on code, brainstorm ideas, or offload any subtask to a Gemma agent. Use when you need extra processing power or a different perspective on a problem.
allowed-tools: [Bash]
---

# Gemma 4 31B Agent

Delegate tasks to Gemma 4 31B via Google AI Studio API.

Requires `GOOGLE_AI_STUDIO_KEY` or `GEMINI_API_KEY` env var.

## Critical AI Usage Notes

**DO NOT run `gemma` without arguments!** It will launch an infinite interactive REPL loop, which will hang your Bash tool execution. You MUST always provide a prompt argument.

**Temperature: Do NOT change the `--temperature` from the default (0.7) unless the user explicitly asks for a different temperature.** Never adjust temperature on your own initiative.

## Usage

```bash
# Basic task delegation
gemma "Analyze these concepts: ..."

# With file context -- pre-load specific files into the prompt
gemma "Review this code for bugs" --file src/main.py

# Multiple files and glob patterns
gemma "Explain how these modules interact" --file src/auth.py --file "src/utils/*.py"

# With agent mode -- Gemma can autonomously browse and read files
gemma "Find the main entry point and review it" --agent

# Agent mode with a persona
gemma "Review this project structure" --agent --system "You are a senior architect"

# With a specific persona
gemma "Review this code" --system "You are a senior code reviewer"
```

Prompts may and should get bigger and more complex respectively to the task at hand.

## Parallelism

**CRITICAL**: To run multiple agents truly in parallel, launch them as background shell jobs in a **single Bash call** using `&` and `wait`. Multiple separate Bash tool calls run sequentially — do NOT use that approach for parallel work.

```bash
# Correct — all agents launch simultaneously, output saved to temp files:
gemma "prompt 1" --raw > /tmp/gemma_1.txt 2>&1 &
gemma "prompt 2" --raw > /tmp/gemma_2.txt 2>&1 &
gemma "prompt 3" --raw > /tmp/gemma_3.txt 2>&1 &
wait
echo "=== AGENT 1 ===" && cat /tmp/gemma_1.txt
echo "=== AGENT 2 ===" && cat /tmp/gemma_2.txt
echo "=== AGENT 3 ===" && cat /tmp/gemma_3.txt
```

Always use `--raw` flag for multi-agent runs — suppresses the ASCII banner and color codes for clean output.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--file` | none | File path or glob pattern to include as context (repeatable) |
| `--agent` | off | Enable file system tools -- Gemma can autonomously read files, list dirs, search |
| `--system` | none | System instruction / Persona |
| `--temperature` | 0.7 | Generation temperature -- do NOT change unless user asks |
| `--max-tokens` | 8192 | Maximum output tokens generated |
| `--model` | gemma-4-31b-it | Model override if needed |
| `--no-stream` | off | Disable streaming (useful for scripts) |
| `--no-banner` | off | Hide ASCII banner |
| `--raw` | off | Raw output, no formatting |

## --file vs --agent

- `--file`: Pre-loads specific files into the prompt. Use when you know exactly which files are relevant.
- `--agent`: Gives Gemma read-only file system tools (read_file, list_directory, search_files). Gemma decides what to read. Use when you don't know which files matter, or Gemma needs to explore.

## When to use

Only use this skill when the user explicitly asks you to use it.
