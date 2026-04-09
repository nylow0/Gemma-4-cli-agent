---
name: gemma
description: This skill should be used when Claude needs to delegate a task to Gemma 4 31B, run parallel research, get a second opinion on code, brainstorm ideas, or offload any subtask to a Gemma agent. Use when you need extra processing power or a different perspective on a problem.
allowed-tools: [Bash]
---

# Gemma 4 31B Agent

Delegate tasks to Gemma 4 31B via Google AI Studio API.

Requires `GOOGLE_AI_STUDIO_KEY` or `GEMINI_API_KEY` env var.

## Critical AI Usage Notes

**⚠️ DO NOT run `gemma` without arguments!** It will launch an infinite interactive REPL loop, which will hang your Bash tool execution. You MUST always provide a prompt argument.
**✅ ALWAYS use the `--raw` flag** when parsing output programmatically. This removes the ASCII art banner and ANSI escape sequences, keeping the output clean for context.

## Usage

```bash
# Basic task delegation
gemma "Analyze these concepts: ..." --raw

# With a specific persona and strict temperature
gemma "Review this code" --system "You are a senior code reviewer" --temperature 0.3 --raw

```
Prompts may and should get bigger and more complex respectively to the task at hand.

Changing the temperature should not be done often, but if you really think this parameter may help the user achieve the best results, you can tune it a little bit, but usually don't touch it.

Use `Bash` tool calls to run multiple Gemma agents simultaneously.
Run it as much times as user asked you to.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--system` | none | System instruction / Persona |
| `--temperature` | 0.7 | Generation temperature (0.0–2.0) |
| `--max-tokens` | 8192 | Maximum output tokens generated |
| `--model` | gemma-4-31b-it | Model override if needed |
| `--no-stream` | off | Disable streaming (useful for scripts) |
| `--no-banner` | off | Hide ASCII banner (implied by --raw) |
| `--raw` | off | Raw output, no formatting, ideal for AI |

## When to use

Only use this skill when the user explicitly asks you to use it. 
