"""
AIRouter: Central intelligence for routing AI tasks to the right model.

Usage:
    router = AIRouter()

    # Text generation
    result = router.complete(
        task="post_generation",
        messages=[{"role": "user", "content": "Write a post..."}],
        json_mode=True,
    )
    print(result["text"])   # The generated text
    print(result["cost_usd"])  # e.g. 0.000234

    # Image generation
    result = router.generate_image(
        task="image_generation",
        prompt="Abstract minimalist...",
    )
    print(result["image_url"])
"""
import logging
import os
from typing import Optional

from linkedin.services.ai_providers import (
    OpenAITextProvider,
    AnthropicProvider,
    GeminiProvider,
    GroqProvider,
    DalleImageProvider,
    StabilityImageProvider,
    ReplicateImageProvider,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING TABLES
# Order within each tier = preference order (tried left to right as fallback)
# ─────────────────────────────────────────────────────────────────────────────
TEXT_ROUTING = {
    "premium":  ["anthropic", "openai", "google"],
    "balanced": ["openai",    "google", "anthropic", "groq"],
    "budget":   ["groq",      "google", "openai"],
}

IMAGE_ROUTING = {
    "premium":  ["dalle",      "replicate"],
    "balanced": ["dalle",      "replicate", "stability"],
    "budget":   ["replicate",  "stability", "dalle"],
}

# Maps task name → which env var controls its tier
TASK_TIER_MAP = {
    # Text tasks
    "post_generation":        "AI_TIER_POST_GENERATION",
    "visual_brief":           "AI_TIER_VISUAL_BRIEF",
    "comment_generation":     "AI_TIER_COMMENTS",
    "connection_message":     "AI_TIER_CONNECTIONS",
    "cover_letter":           "AI_TIER_COVER_LETTERS",
    "profile_optimization":   "AI_TIER_PROFILE_OPTIMIZATION",
    "weekly_report":          "AI_TIER_POST_GENERATION",  # Reuse post tier
    # Image tasks
    "image_generation":       "AI_TIER_IMAGE_GENERATION",
}


class AIRouter:
    """
    Stateless router that picks the best available AI model for a given task.
    Falls back to the next provider in the list if the primary fails.
    Logs cost per call for monitoring.
    """

    def __init__(self):
        # Initialize all providers (lazy — they only connect when called)
        self._text_providers = {
            "openai":    OpenAITextProvider(),
            "anthropic": AnthropicProvider(),
            "google":    GeminiProvider(),
            "groq":      GroqProvider(),
        }
        self._image_providers = {
            "dalle":      DalleImageProvider(),
            "replicate":  ReplicateImageProvider(),
            "stability":  StabilityImageProvider(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC METHODS
    # ─────────────────────────────────────────────────────────────────────────

    def complete(
        self,
        task: str,
        messages: list[dict],
        json_mode: bool = False,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        force_tier: Optional[str] = None,
    ) -> dict:
        """
        Route a text completion task to the best available model.

        Args:
            task: Task name (must be in TASK_TIER_MAP)
            messages: OpenAI-style messages list [{"role": ..., "content": ...}]
            json_mode: Whether to request JSON output
            max_tokens: Maximum output tokens
            temperature: Creativity (0.0–1.0)
            force_tier: Override env var tier (budget/balanced/premium)

        Returns:
            dict with keys: text, model, provider, cost_usd, input_tokens, output_tokens
        """
        tier = force_tier or self._get_tier(task)
        provider_order = TEXT_ROUTING.get(tier, TEXT_ROUTING["balanced"])
        available = [p for p in provider_order if self._text_providers[p].is_available()]

        if not available:
            raise RuntimeError(
                f"No text AI providers available for tier '{tier}'. "
                f"Please set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, "
                f"GOOGLE_AI_API_KEY, GROQ_API_KEY"
            )

        last_error = None
        for provider_name in available:
            provider = self._text_providers[provider_name]
            try:
                result = provider.complete(
                    messages=messages,
                    tier=tier,
                    json_mode=json_mode,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                result["task"] = task
                result["tier"] = tier
                self._log_usage(task, result)
                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[AIRouter] Provider '{provider_name}' failed for task '{task}': {e}. "
                    f"Trying next provider..."
                )
                continue

        raise RuntimeError(
            f"All providers failed for task '{task}' (tier: {tier}). "
            f"Last error: {last_error}"
        )

    def generate_image(
        self,
        task: str,
        prompt: str,
        force_tier: Optional[str] = None,
    ) -> dict:
        """
        Route an image generation task to the best available model.

        Returns:
            dict with keys: image_url, model, provider, cost_usd, revised_prompt
        """
        tier = force_tier or self._get_tier(task)
        provider_order = IMAGE_ROUTING.get(tier, IMAGE_ROUTING["balanced"])
        available = [p for p in provider_order if self._image_providers[p].is_available()]

        if not available:
            raise RuntimeError(
                f"No image AI providers available for tier '{tier}'. "
                f"Please set at least one of: OPENAI_API_KEY, REPLICATE_API_TOKEN, STABILITY_API_KEY"
            )

        last_error = None
        for provider_name in available:
            provider = self._image_providers[provider_name]
            try:
                result = provider.generate(prompt=prompt, tier=tier)
                result["task"] = task
                result["tier"] = tier
                self._log_usage(task, result)
                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[AIRouter] Image provider '{provider_name}' failed for task '{task}': {e}. "
                    f"Trying next provider..."
                )
                continue

        raise RuntimeError(
            f"All image providers failed for task '{task}' (tier: {tier}). "
            f"Last error: {last_error}"
        )

    def get_cheapest_available_text_provider(self) -> str:
        """Returns the name of the cheapest available text provider."""
        for provider_name in TEXT_ROUTING["budget"]:
            if self._text_providers[provider_name].is_available():
                return provider_name
        return "unknown"

    def get_configured_providers(self) -> dict:
        """Returns status of all configured providers (useful for admin dashboard)."""
        return {
            "text": {
                name: provider.is_available()
                for name, provider in self._text_providers.items()
            },
            "image": {
                name: provider.is_available()
                for name, provider in self._image_providers.items()
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _get_tier(self, task: str) -> str:
        """Read the tier for a given task from environment variables."""
        env_var = TASK_TIER_MAP.get(task)
        if not env_var:
            logger.warning(f"[AIRouter] Unknown task '{task}', defaulting to 'balanced'")
            return "balanced"
        return os.environ.get(env_var, "balanced").lower()

    def _log_usage(self, task: str, result: dict):
        """Log AI usage for cost monitoring."""
        cost = result.get("cost_usd", 0)
        model = result.get("model", "unknown")
        provider = result.get("provider", "unknown")
        logger.info(
            f"[AIRouter] Task={task} | Provider={provider} | "
            f"Model={model} | Cost=${cost:.6f}"
        )
        # In production: save to AIUsageLog model for cost dashboards
        # AIUsageLog.objects.create(task=task, model=model, cost=cost, ...)