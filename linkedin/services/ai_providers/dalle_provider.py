"""OpenAI DALL-E image generation provider (DALL-E 3, DALL-E 2)."""
import os
import httpx
from openai import OpenAI


class DalleImageProvider:

    # (model, quality) → cost per image
    TIER_CONFIG = {
        "premium":  {"model": "dall-e-3", "quality": "hd",       "size": "1792x1024", "cost": 0.080},
        "balanced": {"model": "dall-e-3", "quality": "standard", "size": "1792x1024", "cost": 0.040},
        "budget":   {"model": "dall-e-2", "quality": "standard", "size": "1024x1024", "cost": 0.018},
    }

    def __init__(self):
        self.provider_name = "openai_dalle"
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

    def generate(self, prompt: str, tier: str = "balanced") -> dict:
        """
        Generate an image.
        Returns: {"image_url": str, "model": str, "cost_usd": float, "provider": str}
        """
        config = self.TIER_CONFIG.get(tier, self.TIER_CONFIG["balanced"])

        kwargs = {
            "model": config["model"],
            "prompt": prompt,
            "size": config["size"],
            "n": 1,
        }
        if config["model"] == "dall-e-3":
            kwargs["quality"] = config["quality"]
            kwargs["style"] = "vivid"

        client = self._get_client()
        response = client.images.generate(**kwargs)

        return {
            "image_url": response.data[0].url,
            "model": config["model"],
            "cost_usd": config["cost"],
            "provider": self.provider_name,
            "revised_prompt": getattr(response.data[0], "revised_prompt", prompt),
        }