---
name: gemma
description: This skill should be used when Claude needs to delegate a task to Gemma 4 31B, run parallel research, get a second opinion on code, brainstorm ideas, or offload any subtask to a Gemma agent. Use when you need extra processing power or a different perspective on a problem.
allowed-tools: [Bash]
---

# Gemma 4 31B Agent

Delegate tasks to Gemma 4 31B via Google AI Studio API.

Requires `GOOGLE_AI_STUDIO_KEY` or `GEMINI_API_KEY` env var.

## Usage

```bash
gemma "your prompt here"
gemma "your prompt" --system "You are a code reviewer" --temperature 0.3 --max-tokens 4096
```

Call `gemma` multiple times in parallel Bash tool calls to run multiple Gemma agents simultaneously.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--system` | none | System instruction |
| `--temperature` | 0.7 | Generation temperature |
| `--max-tokens` | 8192 | Max output tokens |
| `--model` | gemma-4-31b-it | Model override |
| `--no-stream` | off | Disable streaming |
| `--no-banner` | off | Hide ASCII banner |
| `--raw` | off | Raw output, no formatting |

## When to use

- Offload research or analysis tasks
- Get a second opinion on code changes
- Run multiple parallel investigations
- Brainstorm or generate alternatives
- Any subtask that benefits from delegation
