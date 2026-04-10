---
name: gemma-research
description: Use this skill for multi-agent fan-out and synthesis with the local Gemma CLI when a task benefits from several independent passes, contrasting personas, or broad evidence gathering.
allowed-tools: [Bash, Read, Write]
---

# Gemma Research

This skill orchestrates multiple `gemma` runs, collects the outputs, and synthesizes them in Claude.

Use it for:
- broad research
- comparison work
- brainstorming with diverse lenses
- consensus-seeking across multiple independent runs
- deep dives where separate agents should cover different angles

The current Gemma program adds two important capabilities that this skill should actively use:
- `--system` for clean persona/lens assignment per agent
- `--file` for shared text or multimodal evidence across all agents

## Critical Rules

- Never run `gemma` without a prompt argument. That opens the interactive REPL and blocks the shell call.
- Always use `--raw` for research fan-out. This keeps output parseable and removes banner/thinking noise.
- Treat agent mode as always on. Do not use `--no-agent`.
- Do not rely on `/model`, `/agent`, or other unsupported slash commands.
- Do not change `--temperature` unless the user explicitly asks.
- Prefer up to 5 concurrent Gemma jobs per batch unless the user explicitly wants more aggressive parallelism.
- Synthesize inside Claude after collection. Do not open Gemma interactively for synthesis.

## Research Pattern

### 1. Pick a mode

- `explore`: maximize diversity and idea generation
- `consensus`: independent runs answering the same core question
- `deep`: assign different facets of the same topic
- `compare`: make the strongest case for each option, then cross-check

### 2. Design the runs

For each agent, vary at least one of:
- persona via `--system`
- methodology in the prompt
- scope constraint in the prompt
- target audience in the prompt

Use `--file` when all agents should see the same code, document, screenshot, PDF, or other evidence.

Examples:

```bash
gemma "Evaluate this architecture for operational risk" --system "You are a skeptical staff platform engineer" --file architecture.md --raw
gemma "Find the strongest case for this product direction" --system "You are an optimistic product strategist" --file brief.pdf --raw
gemma "Summarize what this screenshot reveals about the UX failure" --system "You are a detail-oriented UX reviewer" --file screenshot.png --raw
```

### 3. Execute in batches

Run each batch in one shell invocation:

```bash
gemma "PROMPT 1" --system "LENS 1" --raw > /tmp/gemma_research_1.txt 2>&1 &
gemma "PROMPT 2" --system "LENS 2" --raw > /tmp/gemma_research_2.txt 2>&1 &
gemma "PROMPT 3" --system "LENS 3" --raw > /tmp/gemma_research_3.txt 2>&1 &
gemma "PROMPT 4" --system "LENS 4" --raw > /tmp/gemma_research_4.txt 2>&1 &
gemma "PROMPT 5" --system "LENS 5" --raw > /tmp/gemma_research_5.txt 2>&1 &
wait
```

Repeat for later batches if needed.

### 4. Collect and tag results

For each output:
- record the prompt or lens that produced it
- mark failures or empty responses
- keep useful dissent instead of collapsing it away

### 5. Synthesize in Claude

Apply these rules:
- disagreement is signal
- deduplicate overlaps
- weight specific evidence over vague claims
- keep minority positions visible when they are well argued
- note when several agents converge suspiciously fast on the same generic answer

## Mode Guidance

### Explore

- Maximize divergence.
- Include at least one contrarian or weird-angle run.
- Sort outputs by novelty, not by agreement.

### Consensus

- Ask the same core question with different personas.
- Count independent agreement.
- Surface disputed claims explicitly.

### Deep

- Assign one facet per run.
- Combine the results into a coherent end-to-end picture.
- Call out uncovered facets.

### Compare

- Give each option at least one advocate run.
- Use additional runs to critique the strongest arguments from the other side.
- End with a recommendation plus the legitimate strengths of the losing option.

## Output Format

Return:
1. the research goal and mode
2. how many Gemma runs were launched and how many produced usable output
3. the synthesized findings
4. confidence and key uncertainties

## When To Use

Use this skill when one Gemma answer is not enough and the task genuinely benefits from structured fan-out and synthesis.
