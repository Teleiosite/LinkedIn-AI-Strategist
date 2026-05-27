"""Replicate provider — Flux Pro and Flux Schnell image generation."""
import os


class ReplicateImageProvider:
    """
    Flux models on Replicate. Flux Schnell is very fast and cheap (~$0.003/image).
    Flux Pro is high quality (~$0.05/image).
    Both produce better abstract/artistic results than DALL-E 2.
    """

    TIER_CONFIG = {
        "premium":  {
            "model": "black-forest-labs/flux-pro",
            "cost": 0.055,
            "params": {"width": 1440, "height": 768, "steps": 25},
        },
        "balanced": {
            "model": "black-forest-labs/flux-schnell",
            "cost": 0.003,
            "params": {"width": 1440, "height": 768, "num_inference_steps": 4},
        },
        "budget": {
            "model": "black-forest-labs/flux-schnell",
            "cost": 0.003,
            "params": {"width": 1024, "height": 576, "num_inference_steps": 4},
        },
    }

    def __init__(self):
        self.provider_name = "replicate_flux"
        self._client = None

    def _get_client(self):
        if self._client is None:
            import replicate
            self._client = replicate
        return self._client

    def is_available(self) -> bool:
        return bool(os.environ.get("REPLICATE_API_TOKEN"))

    def generate(self, prompt: str, tier: str = "balanced") -> dict:
        replicate = self._get_client()
        config = self.TIER_CONFIG.get(tier, self.TIER_CONFIG["balanced"])

        output = replicate.run(
            config["model"],
            input={"prompt": prompt, **config["params"]}
        )

        # Replicate returns a list of URLs or a FileOutput object
        image_url = str(output[0]) if isinstance(output, list) else str(output)

        return {
            "image_url": image_url,
            "model": config["model"],
            "cost_usd": config["cost"],
            "provider": self.provider_name,
            "revised_prompt": prompt,
        }