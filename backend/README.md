# Yar backend

Python agent + stdlib API server. See [`AGENTS.md`](AGENTS.md) and
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

```bash
uv sync --extra eval --extra dev
cp .env.example .env   # set OPENAI_API_KEY; YAR_BASE_URL defaults to AvalAI
uv run pytest -q evals/deterministic/test_text.py evals/deterministic/test_config.py
```
