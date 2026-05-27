"""
ContentService: Generates LinkedIn post text using the AI Router.
"""
import json
import logging

from linkedin.models import LinkedInProfile, GeneratedPost
from linkedin.services.prompt_engine import PromptEngine, UserContext
from linkedin.services.ai_router import AIRouter

logger = logging.getLogger(__name__)


class ContentService:

    def __init__(self):
        self.router = AIRouter()

    def generate_post(
        self,
        profile: LinkedInProfile,
        post_type: str,
        recent_topics: list[str] = None
    ) -> dict:
        """
        Generate a LinkedIn post for the given profile.
        Returns dict with post_text, hook, hashtags, core_message, target_emotion, model, provider, cost_usd.
        """
        ctx = self._build_user_context(profile)

        # Build prompts
        system_prompt = PromptEngine.get_system_prompt(ctx)
        user_prompt = PromptEngine.get_post_generation_prompt(post_type, recent_topics)

        # Call AI Router
        response = self.router.complete(
            task="post_generation",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            json_mode=True,
            temperature=0.8,
        )

        result = json.loads(response["text"])
        result["cost_usd"] = response["cost_usd"]
        result["model"] = response["model"]
        result["provider"] = response["provider"]

        logger.info(f"Generated {post_type} post for profile {profile.id}, cost: ${response['cost_usd']:.4f}")
        return result

    def generate_comment(
        self,
        profile: LinkedInProfile,
        target_post_text: str,
        target_author_name: str
    ) -> str:
        """Generate a thoughtful comment for a target LinkedIn post."""
        ctx = self._build_user_context(profile)
        prompt = PromptEngine.get_comment_prompt(ctx, target_post_text, target_author_name)

        response = self.router.complete(
            task="comment_generation",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )

        return response["text"].strip()

    def generate_connection_message(
        self,
        profile: LinkedInProfile,
        target_name: str,
        target_headline: str,
        target_company: str,
        reason: str
    ) -> str:
        """Generate a personalized connection request message."""
        ctx = self._build_user_context(profile)
        prompt = PromptEngine.get_connection_request_prompt(
            ctx, target_name, target_headline, target_company, reason
        )

        response = self.router.complete(
            task="connection_message",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=100
        )

        return response["text"].strip()

    def generate_cover_letter(
        self,
        profile: LinkedInProfile,
        job_title: str,
        company: str,
        job_description: str
    ) -> str:
        """Generate a cover letter for a job application."""
        ctx = self._build_user_context(profile)
        prompt = PromptEngine.get_cover_letter_prompt(
            ctx, job_title, company, job_description
        )

        response = self.router.complete(
            task="cover_letter",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=400
        )

        return response["text"].strip()

    def _build_user_context(self, profile: LinkedInProfile) -> UserContext:
        skills = [s.strip() for s in profile.skills.split(",") if s.strip()]
        return UserContext(
            goal=profile.goal,
            industry=profile.target_industry,
            role=profile.target_role,
            skills=skills,
            bio=profile.bio_summary,
            location=profile.target_location,
            brand_primary_color=profile.brand_primary_color,
            brand_secondary_color=profile.brand_secondary_color,
        )