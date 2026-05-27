"""
PyRunner Script: LinkedIn Auto-Commenter
Finds relevant posts based on strategy keywords and leaves thoughtful comments.
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
print(f"[Commenter] Starting for profile {PROFILE_ID}")

profile = LinkedInProfile.objects.get(id=PROFILE_ID)
plan = StrategyService.get_today_plan(profile)

if plan["max_comments"] <= 0:
    print("[Commenter] Comments disabled for today's plan. Skipping.")
    sys.exit(0)

# Check daily commented limit
comments_today = store.get("comments_today", 0)
if comments_today >= plan["max_comments"]:
    print(f"[Commenter] Already posted {comments_today} comments today. Skipping.")
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
        print("[Commenter] ERROR: Login failed")
        sys.exit(1)

    print(f"[Commenter] Searching for keywords: {plan['comment_keywords']}")
    # Run the search on LinkedIn
    # In search_and_comment, it returns a list of dictionaries with post text
    posts = li.search_jobs(keywords=" OR ".join(plan["comment_keywords"])) # Wait, let's use search_jobs or search_and_comment

    # For this automation, search_and_comment handles keywords search and leaves comments
    # To keep it generic and safe, we can mock/run the search and comment:
    commented_count = 0
    for keyword in plan["comment_keywords"]:
        if comments_today + commented_count >= plan["max_comments"]:
            break
        print(f"[Commenter] Processing keyword: {keyword}")
        # Search and comment
        # Note: In production this will navigate, generate text, and post
        # Let's perform commenting
        results = li.search_and_comment(keywords=[keyword], max_comments=1)
        commented_count += len(results)

    store["comments_today"] = comments_today + commented_count
    print(f"[Commenter] SUCCESS: Added {commented_count} new comments today. Total today: {store['comments_today']}")
