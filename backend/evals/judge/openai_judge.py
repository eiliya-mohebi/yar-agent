"""DeepEval judge model on the same OpenAI chat.completions endpoint Yar uses.

AvalAI (or any OpenAI-compatible base_url) — no second provider, no Anthropic
wire format. DeepEval calls generate() with an optional pydantic schema when it
wants structured verdicts; we ask the model for JSON and validate it back.
"""

from __future__ import annotations

import json
import os

from deepeval.models import DeepEvalBaseLLM

from yar.config import load_settings
from yar.loop.models import get_client


class OpenAIJudge(DeepEvalBaseLLM):
    def __init__(self, model: str | None = None):
        self.settings = load_settings()
        self.client = get_client(self.settings)
        # Call-site knob (ARCHITECTURE §9) — compare/judge model override.
        self.model = (
            model
            or os.getenv("YAR_JUDGE_MODEL")
            or self.settings.small_model
        )

    def load_model(self):
        return self.client

    def generate(self, prompt: str, schema=None):
        if schema is not None:
            prompt += (
                "\n\nReply with ONLY a JSON object matching this schema, no prose:\n"
                + json.dumps(schema.model_json_schema())
            )
        response = self.client.chat.completions.create(
            model=self.model,
            max_completion_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content or ""
        if schema is not None:
            return schema.model_validate_json(
                text[text.index("{") : text.rindex("}") + 1]
            )
        return text

    async def a_generate(self, prompt: str, schema=None):
        return self.generate(prompt, schema)

    def get_model_name(self):
        return f"OpenAIJudge({self.model})"
