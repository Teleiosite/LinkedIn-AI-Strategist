"""Groq provider — Llama 3 70B, ultra-fast, near-free cost."""
import os


class GroqProvider:
    """
    Groq runs open-source models (Llama 3) at extremely low cost and
    very high speed. Best for high-volume, lower-stakes tasks like
    comments, connection messages, and visual brief extraction.
    """

    MODELS = {
        "premium":  "llama3-70b-8192",
        "balanced": "llama3-70b-8192",
        "budget":   "llama3-8b-8192",
    }

    COST_PER_1K = {
        "llama3-70b-8192": {"input": 0.00059, "output": 0.00079},
        "llama3-8b-8192":  {"input": 0.00005, "output": 0.00008},
    }

    def __init__(self):
        self.provider_name = "groq"
        self._client = None

    def _get_client(self):
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=os.environ["GROQ_API_KEY"])
        return self._client

    def is_available(self) -> bool:
        return bool(os.environ.get("GROQ_API_KEY"))

    def complete(
        self,
        messages: list[dict],
        tier: str = "budget",
        json_mode: bool = False,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> dict:
        client = self._get_client()
        model = self.MODELS.get(tier, self.MODELS["budget"])

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content

        costs = self.COST_PER_1K.get(model, {"input": 0.001, "output": 0.001})
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