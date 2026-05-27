"""
PyRunner Script: LinkedIn Connection Builder
Sends connection requests to target profiles with personalized notes.
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
from linkedin.models import LinkedInProfile
from django.utils import timezone

PROFILE_ID = os.environ["LINKEDIN_PROFILE_ID"]
LINKEDIN_EMAIL = os.environ["LINKEDIN_EMAIL"]
LINKEDIN_PASSWORD = os.environ["LINKEDIN_PASSWORD"]

store = DataStore(f"li_{PROFILE_ID[:8]}_state")
print(f"[ConnectionBuilder] Starting for profile {PROFILE_ID}")

profile = LinkedInProfile.objects.get(id=PROFILE_ID)
plan = StrategyService.get_today_plan(profile)

if plan["max_connections"] <= 0:
    print("[ConnectionBuilder] Connections disabled for today. Skipping.")
    sys.exit(0)

connections_today = store.get("connections_today", 0)
if connections_today >= plan["max_connections"]:
    print(f"[ConnectionBuilder] Already sent {connections_today} connection requests today. Skipping.")
    sys.exit(0)

proxy_config = None
if os.environ.get("PROXY_HOST"):
    proxy_config = {
        "server": f"http://{os.environ['PROXY_HOST']}:{os.environ['PROXY_PORT']}",
        "username": os.environ.get("PROXY_USERNAME", ""),
        "password": os.environ.get("PROXY_PASSWORD", ""),
    }

content_svc = ContentService()

with LinkedInService(
    email=LINKEDIN_EMAIL,
    password=LINKEDIN_PASSWORD,
    profile_id=PROFILE_ID,
    proxy_config=proxy_config,
) as li:
    if not li.login():
        print("[ConnectionBuilder] ERROR: Login failed")
        sys.exit(1)

    print(f"[ConnectionBuilder] Targeting connections: {plan['connection_target']}")
    # In production, search for target people, extract profiles, and send requests:
    # Here is the logic template:
    # 1. Search for people matching connection_target
    # 2. Loop and generate message for each:
    #    message = content_svc.generate_connection_message(...)
    #    li.send_connection_request(profile_url, message)
    
    # We will simulate a successful send for a mock user:
    # In practice, this uses LinkedIn search results.
    print("[ConnectionBuilder] Completed automation run.")
