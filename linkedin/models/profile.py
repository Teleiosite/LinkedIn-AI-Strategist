"""
LinkedInProfile: Stores each user's LinkedIn account connection.
One user can have one LinkedIn profile connected.
"""
import uuid
from django.db import models
from django.conf import settings


class LinkedInProfile(models.Model):

    class Goal(models.TextChoices):
        GET_JOB = "get_job", "Get a Job"
        GET_CLIENTS = "get_clients", "Get Clients"
        BUILD_BRAND = "build_brand", "Build Personal Brand"
        GROW_BUSINESS = "grow_business", "Grow My Business"

    class Aggression(models.TextChoices):
        CONSERVATIVE = "conservative", "Conservative (safe, slow)"
        BALANCED = "balanced", "Balanced (recommended)"
        AGGRESSIVE = "aggressive", "Aggressive (fast, higher risk)"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Setup"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ERROR = "error", "Error - Action Required"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="linkedin_profile"
    )

    # Goal & Strategy
    goal = models.CharField(max_length=30, choices=Goal.choices)
    aggression = models.CharField(
        max_length=20,
        choices=Aggression.choices,
        default=Aggression.BALANCED
    )
    target_industry = models.CharField(max_length=100, blank=True)
    target_role = models.CharField(max_length=100, blank=True)
    target_location = models.CharField(max_length=100, blank=True)
    skills = models.TextField(blank=True, help_text="Comma-separated skills")
    bio_summary = models.TextField(blank=True, help_text="User's background and experience")

    # LinkedIn Credentials (stored via PyRunner Secrets - only store the secret key name)
    credentials_secret_key = models.CharField(
        max_length=100, blank=True,
        help_text="PyRunner Secret key name storing LinkedIn credentials"
    )

    # PyRunner Integration
    # Each user gets their own DataStore for state tracking
    datastore_name = models.CharField(max_length=100, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    status_message = models.TextField(blank=True)

    # LinkedIn Profile Data (fetched after connection)
    linkedin_id = models.CharField(max_length=100, blank=True)
    linkedin_name = models.CharField(max_length=200, blank=True)
    linkedin_headline = models.CharField(max_length=300, blank=True)
    linkedin_url = models.URLField(blank=True)
    profile_picture_url = models.URLField(blank=True)
    connections_count = models.IntegerField(default=0)

    # Module Toggles
    module_posting = models.BooleanField(default=True)
    module_commenting = models.BooleanField(default=True)
    module_connecting = models.BooleanField(default=True)
    module_job_applying = models.BooleanField(default=False)
    module_client_hunting = models.BooleanField(default=False)

    # Limits (per day)
    max_connections_per_day = models.IntegerField(default=20)
    max_comments_per_day = models.IntegerField(default=15)
    max_applications_per_day = models.IntegerField(default=10)

    # Branding
    brand_primary_color = models.CharField(max_length=7, default="#1B4F72")
    brand_secondary_color = models.CharField(max_length=7, default="#F39C12")
    brand_watermark_text = models.CharField(max_length=50, blank=True)

    # Posting schedule
    post_days = models.JSONField(default=list, help_text="Days to post [0-6] 0=Monday")
    post_time = models.CharField(max_length=5, default="08:00", help_text="HH:MM")
    posts_per_week = models.IntegerField(default=3)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "linkedin_profiles"

    def __str__(self):
        return f"{self.user.email} - LinkedIn ({self.goal})"

    @property
    def is_connected(self):
        return bool(self.linkedin_id) and self.status == self.Status.ACTIVE

    @property
    def datastore_key_prefix(self):
        return f"li_{str(self.id)[:8]}"