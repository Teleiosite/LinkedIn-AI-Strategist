"""
GeneratedPost: Every AI-generated LinkedIn post with its image.
"""
import uuid
from django.db import models


class GeneratedPost(models.Model):

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved - Queued to Post"
        POSTED = "posted", "Posted to LinkedIn"
        FAILED = "failed", "Failed to Post"
        REJECTED = "rejected", "Rejected by User"

    class PostType(models.TextChoices):
        THOUGHT_LEADERSHIP = "thought_leadership", "Thought Leadership"
        PERSONAL_STORY = "personal_story", "Personal Story"
        INDUSTRY_INSIGHT = "industry_insight", "Industry Insight"
        ACHIEVEMENT = "achievement", "Achievement/Win"
        TIP_OR_FRAMEWORK = "tip_framework", "Tip or Framework"
        HOT_TAKE = "hot_take", "Hot Take/Opinion"
        CASE_STUDY = "case_study", "Case Study"

    class ImageFormat(models.TextChoices):
        ABSTRACT_SCENE = "abstract_scene", "Abstract Conceptual Scene"
        BOLD_STATEMENT = "bold_statement", "Bold Typography Card"
        BEFORE_AFTER = "before_after", "Before & After Split"
        INFOGRAPHIC_ART = "infographic_art", "Infographic Art Card"
        SYMBOLIC_OBJECT = "symbolic_object", "Symbolic Object"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        "linkedin.LinkedInProfile",
        on_delete=models.CASCADE,
        related_name="posts"
    )

    # Content
    post_type = models.CharField(max_length=30, choices=PostType.choices)
    post_text = models.TextField()
    hook = models.CharField(max_length=300, blank=True, help_text="First line of post (the hook)")
    hashtags = models.TextField(blank=True, help_text="Space-separated hashtags")

    # Image
    image_format = models.CharField(max_length=30, choices=ImageFormat.choices)
    image_prompt_used = models.TextField(blank=True, help_text="DALL-E prompt that generated this image")
    image_url = models.URLField(blank=True, help_text="DALL-E generated image URL")
    image_local_path = models.CharField(max_length=500, blank=True, help_text="Local processed image path")
    image_emotion = models.CharField(max_length=100, blank=True)
    image_metaphor = models.CharField(max_length=200, blank=True)
    image_color_palette = models.CharField(max_length=100, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    linkedin_post_id = models.CharField(max_length=200, blank=True)
    failure_reason = models.TextField(blank=True)

    # Performance (fetched after posting)
    impressions = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    engagement_rate = models.FloatField(default=0.0)

    # AI Metadata
    text_model_used = models.CharField(max_length=50, default="gpt-4o")
    image_model_used = models.CharField(max_length=50, default="dall-e-3")
    text_provider = models.CharField(max_length=50, default="openai")
    image_provider = models.CharField(max_length=50, default="openai")
    generation_cost_usd = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    @property
    def gpt_model_used(self):
        return self.text_model_used

    @property
    def dalle_model_used(self):
        return self.image_model_used

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "linkedin_posts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post [{self.status}] - {self.hook[:50] if self.hook else self.post_text[:50]}"