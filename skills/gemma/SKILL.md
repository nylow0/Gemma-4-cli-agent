---
name: gemma
description: Use this skill when Claude needs to delegate a bounded task to the local Gemma CLI, get a second opinion, offload a subtask, or use Gemma's read-only agent tools or multimodal file handling.
allowed-tools: [Bash]
---

# Gemma CLI Delegation

Delegate a single task to the local `gemma` CLI.

The current program supports:
- agent mode (always on, no flag toggles it)
- read-only file and web tools plus Google Search
- multimodal `--file` input for text, images, video, audio, and PDFs
- system personas via `--system`
- thinking blocks in TTY mode
- an interactive REPL with slash commands for human use

It requires `GOOGLE_AI_STUDIO_KEY` or `GEMINI_API_KEY` in the environment.

## Critical Rules

- Never run `gemma` with no prompt from Claude Code automation. That starts the interactive REPL and blocks the shell call.
- Agent mode is always on. There is no flag to disable it.
- Use `--raw` whenever Claude needs machine-clean output or when you launch concurrent Gemma jobs. `--raw` suppresses banner/color output and strips thinking blocks from stdout.
- Do not change `--temperature` unless the user explicitly asks for a different value.
- Use `--system` for lens/persona changes instead of stuffing that instruction into a long prompt when a clean role separation helps.
- Use `--file` whenever specific local context should be guaranteed in the prompt. Works for text files and media files.
- Do not rely on unsupported controls such as `--no-agent`, `--no-stream`, `/model`, or `/agent`. They do not exist.

## Normal Usage

```bash
gemma "Review this algorithm for edge cases"
gemma "Explain how these modules interact" --file src/auth.py --file "src/utils/*.py"
gemma "Review this code as a senior Python engineer" --system "You are a senior Python code reviewer"
gemma "Summarize the important findings only" --raw
```

## Multimodal Usage

`--file` is no longer text-only.

Use it for:
- source files or config files you want injected into the prompt
- screenshots and images
- video clips
- audio recordings
- PDFs

Examples:

```bash
gemma "What is broken in this UI?" --file screenshot.png
gemma "Transcribe and summarize this call" --file meeting.mp3
gemma "Extract the key constraints from this spec" --file design.pdf
```

## Interactive Mode

For human-driven use, running `gemma` with no prompt opens the interactive interface.

Claude Code should avoid that for automation, but the supported slash commands are:
- `/help`
- `/clear`
- `/system [text]`
- `/file <path>`
- `/files`
- `/think`
- `/temp <0.0-2.0>`
- `/exit`
- `/quit`

Do not mention or depend on `/model` or `/agent`; they are not implemented.

## Parallel Delegation

If you need multiple Gemma calls in parallel, launch them in one shell invocation with background jobs and `wait`. Separate shell tool calls are not true parallelism.

```bash
gemma "Prompt 1" --raw > /tmp/gemma_1.txt 2>&1 &
gemma "Prompt 2" --raw > /tmp/gemma_2.txt 2>&1 &
gemma "Prompt 3" --raw > /tmp/gemma_3.txt 2>&1 &
wait
cat /tmp/gemma_1.txt /tmp/gemma_2.txt /tmp/gemma_3.txt
```

## Choosing Between Prompt, System, and File

- Put the task itself in the main prompt.
- Put stable role framing in `--system`.
- Put concrete repo files or media artifacts in `--file`.
- Prefer `--raw` for any result Claude will parse, compare, or synthesize.

## When To Use

Use this skill when the user wants Gemma specifically, or when a second model pass is materially useful and the overhead is justified.
