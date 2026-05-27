"""
StrategyService: Maps user goals to specific action plans.
Decides what to do each day based on the user's goal and aggression level.
"""
import random
from linkedin.models import LinkedInProfile


class StrategyService:

    # Actions available per module
    DAILY_ACTION_PLAN = {
        "get_job": {
            "conservative": {
                "posts_per_week": 2,
                "comments_per_day": 5,
                "connections_per_day": 10,
                "applications_per_day": 5,
                "post_types": ["thought_leadership", "personal_story", "tip_framework"],
                "comment_keywords": [],  # Set dynamically from target_role
                "connection_targets": "recruiters and hiring managers in {industry}",
            },
            "balanced": {
                "posts_per_week": 3,
                "comments_per_day": 10,
                "connections_per_day": 20,
                "applications_per_day": 10,
                "post_types": ["thought_leadership", "personal_story", "tip_framework",
                               "industry_insight", "achievement"],
            },
            "aggressive": {
                "posts_per_week": 5,
                "comments_per_day": 20,
                "connections_per_day": 30,
                "applications_per_day": 20,
                "post_types": ["thought_leadership", "personal_story", "tip_framework",
                               "industry_insight", "achievement", "hot_take"],
            },
        },
        "get_clients": {
            "conservative": {
                "posts_per_week": 3,
                "comments_per_day": 8,
                "connections_per_day": 10,
                "post_types": ["thought_leadership", "case_study", "tip_framework"],
            },
            "balanced": {
                "posts_per_week": 4,
                "comments_per_day": 15,
                "connections_per_day": 20,
                "post_types": ["thought_leadership", "case_study", "tip_framework",
                               "personal_story", "achievement"],
            },
        },
        "build_brand": {
            "balanced": {
                "posts_per_week": 5,
                "comments_per_day": 20,
                "connections_per_day": 25,
                "post_types": ["thought_leadership", "hot_take", "industry_insight",
                               "personal_story", "tip_framework"],
            },
        },
    }

    @classmethod
    def get_today_plan(cls, profile: LinkedInProfile) -> dict:
        """Return the action plan for today based on profile settings."""
        goal = profile.goal
        aggression = profile.aggression

        base_plan = (
            cls.DAILY_ACTION_PLAN
            .get(goal, {})
            .get(aggression, cls.DAILY_ACTION_PLAN.get(goal, {}).get("balanced", {}))
        )

        # Pick today's post type
        post_types = base_plan.get("post_types", ["thought_leadership"])
        today_post_type = random.choice(post_types)

        return {
            "should_post_today": cls._should_post_today(profile),
            "post_type": today_post_type,
            "max_comments": min(
                base_plan.get("comments_per_day", 10),
                profile.max_connections_per_day
            ),
            "max_connections": min(
                base_plan.get("connections_per_day", 20),
                profile.max_connections_per_day
            ),
            "max_applications": profile.max_applications_per_day,
            "comment_keywords": cls._get_comment_keywords(profile),
            "connection_target": cls._get_connection_target(profile),
        }

    @classmethod
    def _should_post_today(cls, profile: LinkedInProfile) -> bool:
        """Check if today is a scheduled posting day."""
        from django.utils import timezone
        today_weekday = timezone.now().weekday()  # 0=Monday

        if profile.post_days:
            return today_weekday in profile.post_days

        # Default: Mon, Wed, Fri if not set
        return today_weekday in [0, 2, 4]

    @classmethod
    def _get_comment_keywords(cls, profile: LinkedInProfile) -> list[str]:
        """Generate search keywords for finding posts to comment on."""
        keywords = []
        if profile.target_industry:
            keywords.append(profile.target_industry)
        if profile.target_role:
            keywords.append(profile.target_role)
        skills = [s.strip() for s in profile.skills.split(",")[:3] if s.strip()]
        keywords.extend(skills)
        return keywords[:5]

    @classmethod
    def _get_connection_target(cls, profile: LinkedInProfile) -> str:
        """Define who to connect with based on goal."""
        targets = {
            "get_job": f"recruiters and hiring managers in {profile.target_industry}",
            "get_clients": f"business owners and decision makers who might need {profile.target_role}",
            "build_brand": f"thought leaders and professionals in {profile.target_industry}",
            "grow_business": f"potential partners and clients in {profile.target_industry}",
        }
        return targets.get(profile.goal, "relevant professionals in your industry")