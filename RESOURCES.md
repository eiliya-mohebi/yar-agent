# Yar Agent Curriculum Resources

## Knowledge

### Primary (this repo — ground truth for Yar)

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
  How Yar wires Harness / Loop / Memory / Eval. Use for: every pillar lesson, file paths, design cuts.
- [AGENTS.md](AGENTS.md)
  Project rules and the "four pillars stay legible" bar. Use for: scope, stack locks, bilingual text rules.
- [backend/yar/loop/agent.py](backend/yar/loop/agent.py)
  The ~95-line reason → act → observe loop. Use for: Loop pillar, guardrails.
- [backend/yar/app.py](backend/yar/app.py)
  Assembly: `Yar.respond()` turn. Use for: end-to-end message path.
- [waku-agent @ 871c4ac](https://github.com/ShenSeanChen/waku-agent/tree/871c4ac)
  Reference implementation Yar ports. Use for: comparing literals when docs specify contracts only.

### External (general agent architecture)

- [Article: Building Effective Agents — Anthropic (Dec 2024)](https://www.anthropic.com/engineering/building-effective-agents)
  Agents ≈ LLM + tools + feedback in a loop; prefer simple composable patterns over heavy frameworks.
  Use for: defining "agent", when to use agents, stop conditions / max iterations.
- [Guide: OpenAI Agents — Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)
  Runtime loop, sessions vs history, pause/resume. Use for: Harness/runtime state contrast with Yar's Session.
- [Cookbook: Building Reliable Agents with Memory and Compaction — OpenAI](https://developers.openai.com/cookbook/examples/agents_sdk/building_reliable_agents_memory_compaction)
  Short-term context vs durable memory; compaction boundaries. Use for: Memory pillar framing.
- [Docs: LangSmith evaluation types](https://docs.langchain.com/langsmith/evaluation-types)
  Code/heuristic evaluators vs LLM-as-judge. Use for: why Yar never mixes deterministic and judge suites.

## Wisdom (Communities)

- [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/)
  Practitioners discussing local / self-hosted agent stacks. Use for: reality-check on harness choices.
- [Anthropic Discord / engineering discussions](https://www.anthropic.com/)
  Follow engineering posts and threads around agent patterns. Use for: evolving best practice, not API trivia.

## Gaps

- High-quality **Persian** primary literature on agent architecture is thin; bilingual lessons must
  translate carefully from English sources + this repo rather than invent Persian jargon.
- No single canonical paper that uses Yar's exact four-pillar names; pillars are a teaching lens
  aligned with Yar's ARCHITECTURE.md, mapped onto industry patterns above.
