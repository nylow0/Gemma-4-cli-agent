---
name: gemma-research
description: Multi-agent research orchestration using Gemma 4. Fan out N agents with diverse cognitive lenses, collect results, synthesize into a structured report. Use for any research task that benefits from multiple perspectives — brainstorming, finding the best solution, deep analysis, or comparing options.
allowed-tools: [Bash, Read, Write]
---

# Gemma Research — Multi-Agent Research Orchestration

This skill implements **fan-out/fan-in** and **stochastic consensus** patterns to produce high-quality research by running multiple Gemma agents in parallel with diverse cognitive lenses, then synthesizing their outputs.

## When to Use

Use this skill when the user asks you to research something, explore ideas, find the best option, deeply understand a topic, or compare alternatives — and the task would benefit from multiple independent perspectives rather than a single answer.

## Critical Rules

- **NEVER run `gemma` without a prompt argument** — it launches an interactive REPL that hangs Bash.
- **Always use `--raw`** on every gemma call — suppresses banners and colors for clean output.
- **Do NOT change `--temperature`** unless the user explicitly asks.
- **Max 5 agents per batch** — use shell background jobs (`&` + `wait`) within a single Bash call.
- **Always switch to Sonnet model for synthesis** — it has the larger context window needed to ingest all agent reports. Output `/model sonnet` to the user before synthesizing.

## Research Protocol

### Phase 1: Decompose

Analyze the user's query and determine:

1. **Research mode** (auto-detect or user-specified):

| Mode | When | Signal words |
|------|------|-------------|
| **explore** | Brainstorming, generating ideas, creative options | "ideas", "possibilities", "brainstorm", "what could", "alternatives" |
| **consensus** | Finding the best answer, factual questions, recommendations | "best", "should I", "recommend", "which one", "what is" |
| **deep** | Comprehensive understanding of a topic | "explain", "understand", "how does", "deep dive", "comprehensive" |
| **compare** | Choosing between specific options | "vs", "compare", "which is better", "pros and cons", "A or B" |

2. **Agent count** (N): Default 10. Range 5-15 based on complexity. Simple factual = 5, complex multi-faceted = 10-15.

3. **Sub-queries or angles**: Based on mode, break the research into distinct angles (see Phase 2).

### Phase 2: Generate Diverse Prompts

Each agent MUST get a unique prompt that combines elements from the 5 diversity axes below. The goal is **cognitive friction** — agents should NOT converge on the same "safe" answer.

#### Diversity Axes

**Axis 1 — Persona (who)**
Skeptic, Optimist, Academic Researcher, Hands-on Practitioner, End-user/Consumer, Contrarian/Devil's Advocate, Futurist, Historian, Data Scientist, Cross-domain Generalist

**Axis 2 — Perspective Lens (angle)**
- Six Thinking Hats: White (pure facts/data), Red (intuition/gut feel), Black (risks/flaws), Yellow (benefits/value), Green (creative alternatives), Blue (meta-process)
- PESTEL: Political, Economic, Sociocultural, Technological, Environmental, Legal
- Dialectical: Thesis, Antithesis, Synthesis

**Axis 3 — Methodology (how to think)**
First principles decomposition, Analogical reasoning (find parallels in other domains), Falsification testing (try to prove it wrong), Backwards induction (start from desired end state), Quantitative/data-driven analysis

**Axis 4 — Constraints (boundaries)**
"Only use academic/scientific sources", "Focus only on developments from the last 6 months", "Ignore the most popular answer and find alternatives", "Consider only non-Western perspectives", "Focus on edge cases and failure modes"

**Axis 5 — Audience Framing (target)**
Executive brief (ROI/bottom line), Technical deep-dive (implementation details), Skeptical investor (find weaknesses), Policy maker (societal impact), Beginner (explain simply)

#### Mode-Specific Prompt Strategy

**Explore mode**: Maximize divergence. Each agent gets a DIFFERENT persona + methodology + constraint combination. Include at least 2 "contrarian" or "weird angle" agents. Example prompt structure:
> "You are a [PERSONA]. Research: [QUERY]. Use [METHODOLOGY] reasoning. [CONSTRAINT]. Provide your unique perspective — do NOT give a generic answer. Surprising, non-obvious insights are more valuable than safe ones. Use Google Search to find current information."

**Consensus mode**: Same core question, but each agent has a different persona to prevent sycophantic convergence. Example:
> "You are a [PERSONA]. Independently research and answer: [QUERY]. Provide your honest assessment with evidence. Do NOT hedge — commit to a clear answer. Use Google Search for current data."

**Deep mode**: Each agent covers a different PESTEL facet or domain angle. Example:
> "Research [QUERY] focusing EXCLUSIVELY on the [FACET] dimension. Go deep on this single angle. Use Google Search. Provide thorough analysis with specific examples and data."

**Compare mode**: Each agent advocates for a different option. Example:
> "You are an advocate for [OPTION]. Research and make the strongest possible case for [OPTION] over the alternatives. Use Google Search for current data. Be specific with evidence."

### Phase 3: Execute (Fan-Out)

Run agents in batches of up to 5, using shell background jobs in a single Bash call:

```bash
gemma "PROMPT_1" --raw > /tmp/gemma_research_1.txt 2>&1 &
gemma "PROMPT_2" --raw > /tmp/gemma_research_2.txt 2>&1 &
gemma "PROMPT_3" --raw > /tmp/gemma_research_3.txt 2>&1 &
gemma "PROMPT_4" --raw > /tmp/gemma_research_4.txt 2>&1 &
gemma "PROMPT_5" --raw > /tmp/gemma_research_5.txt 2>&1 &
wait
echo "=== Batch 1 complete ==="
```

Then repeat for the next batch (agents 6-10, then 11-15, etc.).

**Important**: Use a timeout of 300000ms (5 minutes) for each Bash call to allow agents time to use Google Search and browse.

### Phase 4: Collect (Fan-In)

After all batches complete:
1. Read each output file using the Read tool
2. Note which agents produced useful output vs empty/error responses
3. Tag each result with the lens combination it was assigned (for traceability in synthesis)

### Phase 5: Synthesize

**Switch to Sonnet model** before synthesizing — tell the user you're switching for the larger context window.

Then synthesize ALL collected agent reports based on mode:

**Explore synthesis**:
- List EVERY unique idea/insight across all agents
- Group by theme, then sort by novelty (most unusual first)
- Outlier ideas that only 1 agent mentioned get their own "Wild Cards" section — these are often the most valuable
- Do NOT filter out "weird" ideas — that's the whole point of explore mode

**Consensus synthesis**:
- Count how many agents independently arrived at each claim/recommendation
- Rank by agreement frequency (e.g., "8/10 agents agree that...")
- Claims with <60% agreement get flagged as "Uncertain / Disputed"
- Show the minority dissent — what did the disagreeing agents say and why?
- Weight by evidence quality: agents that cited sources > unsupported claims

**Deep synthesis**:
- Weave all facets into a comprehensive narrative
- Identify contradictions between agents — these are high-value signal, not noise
- Identify gaps: what important facet did NO agent cover? Note it explicitly.
- Use section headers for each major facet

**Compare synthesis**:
- Build a structured comparison matrix (rows = criteria, columns = options)
- Cross-check: use each advocate's criticisms of other options as counterpoints
- Provide a clear final recommendation with reasoning
- Note where the "losing" option actually has legitimate advantages

### Synthesis Intelligence Rules

These rules apply regardless of mode:
- **Disagreement is signal, not noise** — always surface it explicitly
- **Deduplicate** overlapping findings across agents
- **Weight by evidence**: cited sources and specific data > vague claims
- **Anti-sycophancy**: if all agents suspiciously agree on everything, note that the consensus may be a shared bias rather than truth
- **Failed agents are OK**: N provides redundancy. If 2/10 agents failed, synthesize from the 8 that worked.
- **Traceability**: when citing a specific finding, note which agent (lens) produced it

## Output Format

Present the final synthesis directly to the user as a well-structured report. Include:
1. **Research summary**: what was researched, mode used, N agents deployed, how many returned results
2. **The synthesis** (formatted per mode above)
3. **Confidence assessment**: overall confidence level based on agent agreement and evidence quality
4. **Key uncertainties**: what remains unclear or disputed

## Example Invocation

User: "Research the best backend framework for a startup in 2026"

Claude's actions:
1. Mode: **consensus** (user wants "best")
2. N: 10 agents
3. Generate 10 prompts with diverse personas (Skeptic, Startup CTO, Enterprise Architect, DevOps Engineer, etc.)
4. Run in 2 batches of 5
5. Collect results
6. Switch to Sonnet, synthesize with consensus rules
7. Present ranked report with agreement levels
