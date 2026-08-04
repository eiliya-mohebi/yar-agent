# Yar Curriculum — Lessons

Bilingual (English + Persian) HTML lessons on the **four pillars of agents**, using
[Yar](../README.md) as the readable reference implementation.

**Audience:** public learners who already know LLM basics (chat completions, tool calling).
Not an absolute-beginner LLM course.

**Mission:** see [../MISSION.md](../MISSION.md).

## How to open

Open the index in a browser (no build step):

```bash
# from repo root — example on Linux/WSL
xdg-open lessons/index.html
# or open this file directly:
# lessons/index.html
```

Each lesson has an **EN | فا** language toggle (preference is saved in `localStorage`).
Shared CSS/JS live in [`../assets/`](../assets/).

## Curriculum (read in order)

| # | File | Topic |
|---|------|--------|
| 0001 | [0001-four-pillars.html](0001-four-pillars.html) | Four pillars map |
| 0002 | [0002-the-loop.html](0002-the-loop.html) | Loop — reason → act → observe |
| 0003 | [0003-harness-gateway.html](0003-harness-gateway.html) | Harness / Gateway — move text only |
| 0004 | [0004-memory.html](0004-memory.html) | Memory — semantic / episodic / procedural + gate |
| 0005 | [0005-eval-ops.html](0005-eval-ops.html) | Eval / LLM-Ops — deterministic vs judge, `make gate` |
| 0006 | [0006-one-full-turn.html](0006-one-full-turn.html) | Capstone — one turn through `Yar.respond()` |

Start here: **[index.html](index.html)**

## References

Cheat sheets and glossary (also linked from the index):

- [Glossary](../reference/four-pillars-glossary.html)
- [Loop](../reference/loop-cheatsheet.html) · [Harness](../reference/harness-cheatsheet.html) · [Memory](../reference/memory-cheatsheet.html)
- [Eval / Ops](../reference/eval-cheatsheet.html) · [One turn](../reference/one-turn-cheatsheet.html)

Ground-truth architecture: [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)  
Curated external sources: [../RESOURCES.md](../RESOURCES.md)
