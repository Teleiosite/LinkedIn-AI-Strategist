"""Google Gemini provider (Gemini 1.5 Pro, Gemini 1.5 Flash)."""
import os


class GeminiProvider:

    MODELS = {
        "premium":  "gemini-2.5-pro",
        "balanced": "gemini-3.5-flash",
        "budget":   "gemini-3.5-flash",
    }

    COST_PER_1K = {
        "gemini-2.5-pro":   {"input": 0.00125, "output": 0.005},
        "gemini-3.5-flash": {"input": 0.000075, "output": 0.0003},
    }

    def __init__(self):
        self.provider_name = "google"
        self._client = None

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai
            from linkedin.services.utils import get_env_or_secret
            genai.configure(api_key=get_env_or_secret("GOOGLE_AI_API_KEY"))
            self._client = genai
        return self._client

    def is_available(self) -> bool:
        from linkedin.services.utils import get_env_or_secret
        return bool(get_env_or_secret("GOOGLE_AI_API_KEY"))

    def complete(
        self,
        messages: list[dict],
        tier: str = "balanced",
        json_mode: bool = False,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> dict:
        genai = self._get_client()
        model_name = self.MODELS.get(tier, self.MODELS["balanced"])

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
        )

        # Flatten messages to Gemini format
        prompt = "\n\n".join(
            f"[{m['role'].upper()}]\n{m['content']}" for m in messages
        )

        response = model.generate_content(prompt)
        text = response.text

        # Gemini doesn't always return token counts in all configs — estimate
        input_tokens = len(prompt) // 4
        output_tokens = len(text) // 4
        costs = self.COST_PER_1K.get(model_name, {"input": 0.001, "output": 0.001})
        cost = (
            (input_tokens / 1000 * costs["input"]) +
            (output_tokens / 1000 * costs["output"])
        )

        return {
            "text": text,
            "model": model_name,
            "cost_usd": round(cost, 6),
            "provider": self.provider_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }