"""
PyRunner Script: LinkedIn Job Applier
Searches for relevant jobs and applies with an AI-generated cover letter.
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
from linkedin.models import LinkedInProfile, JobApplication
from django.utils import timezone

PROFILE_ID = os.environ["LINKEDIN_PROFILE_ID"]
LINKEDIN_EMAIL = os.environ["LINKEDIN_EMAIL"]
LINKEDIN_PASSWORD = os.environ["LINKEDIN_PASSWORD"]

store = DataStore(f"li_{PROFILE_ID[:8]}_state")
print(f"[JobApplier] Starting for profile {PROFILE_ID}")

profile = LinkedInProfile.objects.get(id=PROFILE_ID)
plan = StrategyService.get_today_plan(profile)

if plan["max_applications"] <= 0:
    print("[JobApplier] Job applications disabled or set to 0. Skipping.")
    sys.exit(0)

apps_today = store.get("applications_today", 0)
if apps_today >= plan["max_applications"]:
    print(f"[JobApplier] Already applied to {apps_today} jobs today. Skipping.")
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
        print("[JobApplier] ERROR: Login failed")
        sys.exit(1)

    role = profile.target_role or "Software Engineer"
    loc = profile.target_location or "Remote"
    print(f"[JobApplier] Searching for jobs: {role} in {loc}")
    
    jobs = li.search_jobs(keywords=role, location=loc, easy_apply_only=True)
    applied_count = 0

    applied_jobs_cache = store.get("applied_job_ids", [])

    for job in jobs:
        if apps_today + applied_count >= plan["max_applications"]:
            break
            
        job_id = job["url"].split("currentJobId=")[-1].split("&")[0] if "currentJobId=" in job["url"] else job["url"]
        if job_id in applied_jobs_cache:
            continue

        # Generate cover letter
        cover_letter = content_svc.generate_cover_letter(
            profile=profile,
            job_title=job["title"],
            company=job["company"],
            job_description=job.get("description", "")
        )

        print(f"[JobApplier] Applying for {job['title']} at {job['company']}...")
        success = li.apply_to_job(job["url"], cover_letter)

        if success:
            JobApplication.objects.create(
                profile=profile,
                job_title=job["title"],
                company_name=job["company"],
                location=job["location"],
                job_url=job["url"],
                linkedin_job_id=job_id,
                cover_letter_used=cover_letter,
                status=JobApplication.Status.APPLIED
            )
            applied_jobs_cache.append(job_id)
            applied_count += 1

    store["applied_job_ids"] = applied_jobs_cache
    store["applications_today"] = apps_today + applied_count
    print(f"[JobApplier] SUCCESS: Completed {applied_count} new job applications. Total today: {store['applications_today']}")
