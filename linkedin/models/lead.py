"""
Lead: Potential clients identified and tracked by the system.
"""
import uuid
from django.db import models


class Lead(models.Model):

    class Stage(models.TextChoices):
        IDENTIFIED = "identified", "Identified"
        CONNECTION_SENT = "connection_sent", "Connection Request Sent"
        CONNECTED = "connected", "Connected"
        MESSAGE_SENT = "message_sent", "Message Sent"
        REPLIED = "replied", "They Replied"
        MEETING_BOOKED = "meeting_booked", "Meeting Booked"
        CONVERTED = "converted", "Converted to Client"
        NOT_INTERESTED = "not_interested", "Not Interested"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        "linkedin.LinkedInProfile",
        on_delete=models.CASCADE,
        related_name="leads"
    )

    # Lead Details
    linkedin_id = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=200)
    headline = models.CharField(max_length=300, blank=True)
    company = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    profile_url = models.URLField(blank=True)
    profile_picture_url = models.URLField(blank=True)

    # Why they're a lead
    reason = models.TextField(blank=True, help_text="Why this person was identified as a potential client")
    trigger_post = models.TextField(blank=True, help_text="Post/comment that triggered identification")

    # Pipeline
    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.IDENTIFIED)
    connection_message_used = models.TextField(blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    identified_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "linkedin_leads"
        ordering = ["-identified_at"]