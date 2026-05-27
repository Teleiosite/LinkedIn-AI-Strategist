"""
PyRunner Script: LinkedIn Weekly Reporter
Aggregates activity results and sends a summary report email.
"""

import os
import sys

sys.path.insert(0, os.environ.get("DJANGO_PROJECT_PATH", ""))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pyrunner.settings")

import django
django.setup()

from pyrunner_datastore import DataStore
from linkedin.models import LinkedInProfile
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta

PROFILE_ID = os.environ["LINKEDIN_PROFILE_ID"]

store = DataStore(f"li_{PROFILE_ID[:8]}_state")
print(f"[WeeklyReporter] Starting for profile {PROFILE_ID}")

profile = LinkedInProfile.objects.get(id=PROFILE_ID)

# Aggregate stats from models
one_week_ago = timezone.now() - timedelta(days=7)
posts_count = profile.posts.filter(posted_at__gte=one_week_ago).count()
leads_count = profile.leads.filter(identified_at__gte=one_week_ago).count()
applications_count = profile.job_applications.filter(applied_at__gte=one_week_ago).count()

# Reset weekly counters
store["posts_this_week"] = 0

email_subject = f"LinkedIn AI Strategist - Weekly Report for {profile.linkedin_name or profile.user.email}"
email_body = f"""Hello,

Here is your weekly summary report:

- AI-Generated Posts Published: {posts_count}
- New Business Leads Identified: {leads_count}
- Job Applications Sent: {applications_count}

We will reset your weekly targets now and continue driving impact on LinkedIn.

Best regards,
LinkedIn AI Strategist Team
"""

# Send email
try:
    send_mail(
        subject=email_subject,
        message=email_body,
        from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
        recipient_list=[profile.user.email],
        fail_silently=False,
    )
    print("[WeeklyReporter] Report email sent successfully.")
except Exception as e:
    print(f"[WeeklyReporter] ERROR sending email: {e}")
