"""Anthropic Claude provider (Claude 3.5 Sonnet, Claude 3 Haiku)."""
import os


class AnthropicProvider:

    MODELS = {
        "premium":  "claude-3-5-sonnet-20241022",
        "balanced": "claude-3-haiku-20240307",
        "budget":   "claude-3-haiku-20240307",
    }

    COST_PER_1K = {
        "claude-3-5-sonnet-20241022": {"input": 0.003,  "output": 0.015},
        "claude-3-haiku-20240307":    {"input": 0.00025,"output": 0.00125},
    }

    def __init__(self):
        self.provider_name = "anthropic"
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            from linkedin.services.utils import get_env_or_secret
            self._client = anthropic.Anthropic(api_key=get_env_or_secret("ANTHROPIC_API_KEY"))
        return self._client

    def is_available(self) -> bool:
        from linkedin.services.utils import get_env_or_secret
        return bool(get_env_or_secret("ANTHROPIC_API_KEY"))

    def complete(
        self,
        messages: list[dict],
        tier: str = "balanced",
        json_mode: bool = False,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> dict:
        model = self.MODELS.get(tier, self.MODELS["balanced"])
        client = self._get_client()

        # Anthropic uses system message separately
        system_msg = ""
        filtered_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                filtered_messages.append(m)

        if json_mode:
            # Append JSON instruction to system
            system_msg += "\n\nYou must respond with valid JSON only. No markdown, no explanation."

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_msg,
            messages=filtered_messages,
        )

        text = response.content[0].text
        costs = self.COST_PER_1K.get(model, {"input": 0.001, "output": 0.002})
        cost = (
            (response.usage.input_tokens / 1000 * costs["input"]) +
            (response.usage.output_tokens / 1000 * costs["output"])
        )

        return {
            "text": text,
            "model": model,
            "cost_usd": round(cost, 6),
            "provider": self.provider_name,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }