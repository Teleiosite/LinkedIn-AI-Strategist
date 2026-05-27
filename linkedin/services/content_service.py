"""
ContentService: Generates LinkedIn post text using GPT-4o.
"""
import json
import logging
from openai import OpenAI

from linkedin.models import LinkedInProfile, GeneratedPost
from linkedin.services.prompt_engine import PromptEngine, UserContext

logger = logging.getLogger(__name__)


class ContentService:

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate_post(
        self,
        profile: LinkedInProfile,
        post_type: str,
        recent_topics: list[str] = None
    ) -> dict:
        """
        Generate a LinkedIn post for the given profile.
        Returns dict with post_text, hook, hashtags, core_message, target_emotion.
        """
        ctx = self._build_user_context(profile)

        # Build prompts
        system_prompt = PromptEngine.get_system_prompt(ctx)
        user_prompt = PromptEngine.get_post_generation_prompt(post_type, recent_topics)

        # Call GPT-4o
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Track cost (approximate)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens * 0.000005) + (output_tokens * 0.000015)

        result["generation_cost_usd"] = cost
        result["gpt_model_used"] = "gpt-4o"

        logger.info(f"Generated {post_type} post for profile {profile.id}, cost: ${cost:.4f}")
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

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )

        return response.choices[0].message.content.strip()

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

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=100
        )

        return response.choices[0].message.content.strip()

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

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=400
        )

        return response.choices[0].message.content.strip()

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