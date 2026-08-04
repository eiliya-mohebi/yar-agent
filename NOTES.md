# Teaching notes

## Audience & tone
- Public learners who already know LLM basics (chat completions, tools/function calling at a high level).
- Not "hello world ML" — treat them as competent readers who want architecture clarity.
- Concise, concrete, figure-first. Real code from this repo, not pseudocode when possible.

## Format preferences (stated)
- Self-contained HTML with nice fonts and UI
- English **and** Persian, both first-class
- Clear concepts + figures + real code
- Focus curriculum on the **four pillars of every agent**

## UI direction
- Editorial / blueprint feel (ink on paper), not purple-glow AI aesthetic
- Shared stylesheet in `assets/` — every lesson links it
- Language toggle EN | فا on every lesson
- Persian uses `dir="rtl"` + Vazirmatn; English uses a distinctive serif/sans pairing

## Sequencing (working plan)
1. Four pillars map (overview) — lesson 0001
2. The Loop (reason → act → observe) with `loop/agent.py` — lesson 0002
3. Harness / Gateway (CLI + SPA move text only) — lesson 0003
4. Memory (semantic / episodic / procedural + gate) — lesson 0004
5. Eval / LLM-Ops (deterministic vs judge, tracing, release gate) — lesson 0005
6. One full turn through `Yar.respond()` — lesson 0006 (capstone)

Core six-lesson path is complete. Optional later: deep-dives (tools/calendar flagship,
Persian tokenization §7, dashboard API).

## Do not
- Put emojis in lesson UI (repo rule)
- Invent prompt text or FTS DDL — cite / quote real source
- Mix deterministic and judge eval concepts as if they were the same thing
- Include an “Ask your teacher” / follow-up CTA section in lessons (user preference)
