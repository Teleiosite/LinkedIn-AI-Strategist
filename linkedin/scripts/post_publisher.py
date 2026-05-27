"""
PyRunner Script: LinkedIn Post Publisher
Generates and publishes a LinkedIn post with AI-generated image.

Environment variables injected by PyRunner:
- OPENAI_API_KEY (from Secrets)
- LINKEDIN_EMAIL (from Secrets)
- LINKEDIN_PASSWORD (from Secrets)
- LINKEDIN_PROFILE_ID (from Secrets)
- PROXY_HOST, PROXY_PORT, PROXY_USERNAME, PROXY_PASSWORD (from Secrets)
- PYRUNNER_DB_PATH (auto-injected)
"""

import json
import os
import sys

# Add project to path (set by PyRunner's PYTHONPATH)
sys.path.insert(0, os.environ.get("DJANGO_PROJECT_PATH", ""))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pyrunner.settings")

import django
django.setup()

from pyrunner_datastore import DataStore
from linkedin.services.content_service import ContentService
from linkedin.services.image_service import ImageService
from linkedin.services.linkedin_service import LinkedInService
from linkedin.services.strategy_service import StrategyService
from linkedin.models import LinkedInProfile, GeneratedPost
from django.utils import timezone

# ─── Configuration ─────────────────────────────────────
PROFILE_ID = os.environ["LINKEDIN_PROFILE_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
LINKEDIN_EMAIL = os.environ["LINKEDIN_EMAIL"]
LINKEDIN_PASSWORD = os.environ["LINKEDIN_PASSWORD"]

# ─── DataStore for state tracking ──────────────────────
store = DataStore(f"li_{PROFILE_ID[:8]}_state")

# ─── Main Execution ─────────────────────────────────────
print(f"[PostPublisher] Starting for profile {PROFILE_ID}")

# Get profile
profile = LinkedInProfile.objects.get(id=PROFILE_ID)

# Check strategy - should we post today?
plan = StrategyService.get_today_plan(profile)
if not plan["should_post_today"]:
    print("[PostPublisher] Not a posting day. Skipping.")
    sys.exit(0)

# Check posts already made this week
posts_this_week = store.get("posts_this_week", 0)
if posts_this_week >= profile.posts_per_week:
    print(f"[PostPublisher] Already posted {posts_this_week} times this week. Skipping.")
    sys.exit(0)

# Get recent post topics to avoid repetition
recent_topics = store.get("recent_post_topics", [])[-10:]

# ─── Step 1: Generate Post Text ───────────────────────
print(f"[PostPublisher] Generating {plan['post_type']} post...")
content_svc = ContentService()
post_data = content_svc.generate_post(
    profile=profile,
    post_type=plan["post_type"],
    recent_topics=recent_topics
)

post_text = post_data["post_text"]
hashtags = post_data.get("hashtags", "")
full_text = f"{post_text}\n\n{hashtags}"

print(f"[PostPublisher] Post generated. Hook: {post_data.get('hook', '')[:80]}")

# ─── Step 2: Generate Image ──────────────────────────
print(f"[PostPublisher] Generating image...")
visual_brief = content_svc.generate_visual_brief(post_text, plan["post_type"])
image_svc = ImageService()
image_data = image_svc.generate_for_post(
    profile=profile,
    post_text=post_text,
    post_type=plan["post_type"],
    visual_brief=visual_brief
)

print(f"[PostPublisher] Image generated: {image_data['image_format']} / {image_data['image_emotion']}")

# ─── Step 3: Save to Database ────────────────────────
generated_post = GeneratedPost.objects.create(
    profile=profile,
    post_type=plan["post_type"],
    post_text=full_text,
    hook=post_data.get("hook", ""),
    hashtags=hashtags,
    image_format=image_data["image_format"],
    image_prompt_used=image_data["image_prompt_used"],
    image_url=image_data["image_url"],
    image_local_path=image_data["image_local_path"],
    image_emotion=image_data["image_emotion"],
    image_metaphor=image_data["image_metaphor"],
    image_color_palette=image_data["image_color_palette"],
    status=GeneratedPost.Status.APPROVED,
    generation_cost_usd=post_data.get("generation_cost_usd", 0),
)

print(f"[PostPublisher] Saved post {generated_post.id}")

# ─── Step 4: Publish to LinkedIn ─────────────────────
proxy_config = None
if os.environ.get("PROXY_HOST"):
    proxy_config = {
        "server": f"http://{os.environ['PROXY_HOST']}:{os.environ['PROXY_PORT']}",
        "username": os.environ.get("PROXY_USERNAME", ""),
        "password": os.environ.get("PROXY_PASSWORD", ""),
    }

with LinkedInService(
    email=LINKEDIN_EMAIL,
    password=LINKEDIN_PASSWORD,
    profile_id=PROFILE_ID,
    proxy_config=proxy_config,
) as li:
    if not li.login():
        print("[PostPublisher] ERROR: Login failed")
        generated_post.status = GeneratedPost.Status.FAILED
        generated_post.failure_reason = "LinkedIn login failed"
        generated_post.save()
        sys.exit(1)

    result = li.post_content(
        text=full_text,
        image_path=image_data["image_local_path"]
    )

    if result:
        generated_post.status = GeneratedPost.Status.POSTED
        generated_post.posted_at = timezone.now()
        generated_post.save()

        # Update DataStore state
        topics = recent_topics + [post_data.get("core_message", "")]
        store["recent_post_topics"] = topics[-10:]
        store["posts_this_week"] = posts_this_week + 1
        store["total_posts"] = store.get("total_posts", 0) + 1
        store["last_posted_at"] = timezone.now().isoformat()

        print(f"[PostPublisher] SUCCESS: Post published. Total posts: {store['total_posts']}")
    else:
        generated_post.status = GeneratedPost.Status.FAILED
        generated_post.failure_reason = "LinkedIn posting failed"
        generated_post.save()
        print("[PostPublisher] ERROR: Failed to publish post")
        sys.exit(1)