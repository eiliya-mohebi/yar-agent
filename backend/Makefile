# yar-agent — one command per pillar.
#
# PY picks the project venv automatically so you never need to remember
# `source .venv/bin/activate`.
PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)

.PHONY: run brief dashboard trace eval eval-judge gate lint

run:            ## chat with Yar in the terminal (requires OPENAI_API_KEY)
	$(PY) -m yar

brief:          ## morning briefing from calendar + memory
	$(PY) -m yar brief

dashboard:      ## REST/SSE API on 127.0.0.1:7777 (walks +10 if busy)
	$(PY) -m yar dashboard

trace:          ## deep trace waterfalls (Phoenix) at http://localhost:6006
	$(PY) -m phoenix.server.main serve

eval:           ## deterministic evals (0/1, no judge involved)
	$(PY) -m pytest -q evals/deterministic

eval-judge:     ## LLM-as-judge evals (scored %, needs an API key)
	$(PY) -m pytest -q evals/judge

gate:           ## release gate: deterministic must pass; judge when keyed
	$(PY) -m yar.ops.release_gate

lint:
	$(PY) -m ruff check yar evals
