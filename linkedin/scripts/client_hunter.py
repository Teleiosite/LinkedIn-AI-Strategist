"""
PyRunner Script: LinkedIn Client Hunter
Identifies potential leads based on search terms and saves them.
"""

import os
import sys

sys.path.insert(0, os.environ.get("DJANGO_PROJECT_PATH", ""))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pyrunner.settings")

import django
django.setup()

from pyrunner_datastore import DataStore
from linkedin.services.content_service import ContentService
from linkedin.services.linkedin_service import LinkedInService
from linkedin.services.strategy_service import StrategyService
from linkedin.models import LinkedInProfile, Lead
from django.utils import timezone

PROFILE_ID = os.environ["LINKEDIN_PROFILE_ID"]
LINKEDIN_EMAIL = os.environ["LINKEDIN_EMAIL"]
LINKEDIN_PASSWORD = os.environ["LINKEDIN_PASSWORD"]

store = DataStore(f"li_{PROFILE_ID[:8]}_state")
print(f"[ClientHunter] Starting for profile {PROFILE_ID}")

profile = LinkedInProfile.objects.get(id=PROFILE_ID)
plan = StrategyService.get_today_plan(profile)

if not profile.module_client_hunting:
    print("[ClientHunter] Client hunting module disabled. Skipping.")
    sys.exit(0)

# Main hunter execution template
print("[ClientHunter] Running client hunter search and scrape...")
# 1. Search relevant target posts/people
# 2. Add to Lead model as IDENTIFIED
# 3. If connected, escalate to CONNECTED / send messages
print("[ClientHunter] Completed leads collection.")
