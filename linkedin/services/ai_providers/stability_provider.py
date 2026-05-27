"""Stability AI provider — Stable Diffusion 3."""
import os
import httpx
import base64


class StabilityImageProvider:

    TIER_CONFIG = {
        "premium":  {"model": "sd3-large",        "cost": 0.065},
        "balanced": {"model": "sd3-medium",        "cost": 0.035},
        "budget":   {"model": "sd3-medium",        "cost": 0.035},
    }

    API_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"

    def __init__(self):
        self.provider_name = "stability"
        self.api_key = os.environ.get("STABILITY_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, tier: str = "balanced") -> dict:
        config = self.TIER_CONFIG.get(tier, self.TIER_CONFIG["balanced"])

        response = httpx.post(
            self.API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            },
            data={
                "prompt": prompt,
                "model": config["model"],
                "output_format": "png",
                "aspect_ratio": "16:9",
            },
            timeout=60,
        )
        response.raise_for_status()

        data = response.json()
        # Return base64 image as data URL
        image_b64 = data.get("image", "")
        image_url = f"data:image/png;base64,{image_b64}"

        return {
            "image_url": image_url,
            "model": config["model"],
            "cost_usd": config["cost"],
            "provider": self.provider_name,
            "revised_prompt": prompt,
        }