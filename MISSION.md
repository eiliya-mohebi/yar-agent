# Mission: Four Pillars of Agents (via Yar)

## Why
Publish a clear, bilingual (English + Persian) HTML curriculum so a public audience that already
knows LLM basics can *see* how serious agents are built — using Yar as the readable reference
implementation, not a black-box framework.

## Success looks like
- A learner can name the four pillars (Harness, Loop, Memory, Eval/LLM-Ops) and point to the
  real Yar file for each
- They can trace one user message through gateway → session → loop → tools → memory → tracing
- Lessons use figures + real repo code, open as self-contained HTML with a polished UI
- English and Persian are both first-class in every lesson (not an afterthought translation)

## Constraints
- Audience: public; LLM-basics assumed (not absolute beginners)
- Format: self-contained HTML lessons under `lessons/`, shared UI in `assets/`
- Prefer short lessons with one tangible win each
- Ground claims in `RESOURCES.md` and this repo's `docs/` + source — not invent

## Out of scope
- Absolute-beginner LLM/token primer
- Multi-agent orchestration frameworks as the main subject
- Re-adding Yar's deliberately cut features (voice, Telegram, multi-provider, …) as curriculum
  focus — mention seams only when they clarify a pillar
