# yar-agent — one command per pillar.
#
# PY picks the project venv automatically so you never need to remember
# `source .venv/bin/activate`.
PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)

.PHONY: run eval lint

run:            ## chat with Yar in the terminal (requires OPENAI_API_KEY)
	$(PY) -m yar

eval:           ## deterministic evals (0/1, no judge involved)
	$(PY) -m pytest -q evals/deterministic

lint:
	$(PY) -m ruff check yar evals
