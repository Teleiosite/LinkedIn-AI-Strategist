"""OpenAI text completion provider (GPT-4o, GPT-4o-mini)."""
import os
from openai import OpenAI


class OpenAITextProvider:
    """Wraps OpenAI chat completions."""

    MODELS = {
        "premium":  "gpt-4o",
        "balanced": "gpt-4o-mini",
        "budget":   "gpt-4o-mini",
    }

    # Cost per 1k tokens (approximate, update as OpenAI changes pricing)
    COST_PER_1K = {
        "gpt-4o":      {"input": 0.005,   "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    }

    def __init__(self):
        self.provider_name = "openai"
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            from linkedin.services.utils import get_env_or_secret
            self._client = OpenAI(api_key=get_env_or_secret("OPENAI_API_KEY"))
        return self._client

    def is_available(self) -> bool:
        from linkedin.services.utils import get_env_or_secret
        return bool(get_env_or_secret("OPENAI_API_KEY"))

    def complete(
        self,
        messages: list[dict],
        tier: str = "balanced",
        json_mode: bool = False,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> dict:
        """
        Call OpenAI chat completion.
        Returns: {"text": str, "model": str, "cost_usd": float, "provider": str}
        """
        model = self.MODELS.get(tier, self.MODELS["balanced"])
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        client = self._get_client()
        response = client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content

        # Calculate cost
        costs = self.COST_PER_1K.get(model, {"input": 0.001, "output": 0.002})
        cost = (
            (response.usage.prompt_tokens / 1000 * costs["input"]) +
            (response.usage.completion_tokens / 1000 * costs["output"])
        )

        return {
            "text": text,
            "model": model,
            "cost_usd": round(cost, 6),
            "provider": self.provider_name,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }