"""
JobApplication: Tracks every job the system applies to on behalf of the user.
"""
import uuid
from django.db import models


class JobApplication(models.Model):

    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        VIEWED = "viewed", "Application Viewed"
        RESPONDED = "responded", "Employer Responded"
        REJECTED = "rejected", "Rejected"
        INTERVIEW = "interview", "Interview Scheduled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        "linkedin.LinkedInProfile",
        on_delete=models.CASCADE,
        related_name="job_applications"
    )

    # Job Details
    job_title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    job_url = models.URLField()
    linkedin_job_id = models.CharField(max_length=100, blank=True)
    salary_range = models.CharField(max_length=100, blank=True)
    job_description_snippet = models.TextField(blank=True)

    # Application
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    cover_letter_used = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "linkedin_job_applications"
        ordering = ["-applied_at"]