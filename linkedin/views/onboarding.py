"""
Onboarding views: 4-step wizard to set up the LinkedIn Strategist.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpRequest, HttpResponse

from linkedin.models import LinkedInProfile
from linkedin.services.strategy_service import StrategyService
from core.models import Secret, DataStore
from core.services import EncryptionService


@login_required
def onboarding_step1_goal(request: HttpRequest) -> HttpResponse:
    """Step 1: What is your LinkedIn goal?"""
    # Redirect to dashboard if already set up
    if hasattr(request.user, "linkedin_profile"):
        return redirect("linkedin:dashboard")

    if request.method == "POST":
        goal = request.POST.get("goal")
        aggression = request.POST.get("aggression", "balanced")

        if goal not in [g[0] for g in LinkedInProfile.Goal.choices]:
            messages.error(request, "Please select a valid goal.")
            return redirect("linkedin:onboarding_step1")

        # Store in session for multi-step form
        request.session["li_onboarding"] = {
            "goal": goal,
            "aggression": aggression,
        }
        return redirect("linkedin:onboarding_step2")

    return render(request, "linkedin/onboarding/step1_goal.html", {
        "goals": LinkedInProfile.Goal.choices,
        "aggression_levels": LinkedInProfile.Aggression.choices,
    })


@login_required
def onboarding_step2_profile(request: HttpRequest) -> HttpResponse:
    """Step 2: Tell us about yourself."""
    onboarding_data = request.session.get("li_onboarding", {})
    if not onboarding_data.get("goal"):
        return redirect("linkedin:onboarding_step1")

    if request.method == "POST":
        onboarding_data.update({
            "target_industry": request.POST.get("target_industry", ""),
            "target_role": request.POST.get("target_role", ""),
            "target_location": request.POST.get("target_location", ""),
            "skills": request.POST.get("skills", ""),
            "bio_summary": request.POST.get("bio_summary", ""),
            "brand_watermark_text": request.POST.get("brand_watermark_text", ""),
        })
        request.session["li_onboarding"] = onboarding_data
        return redirect("linkedin:onboarding_step3")

    return render(request, "linkedin/onboarding/step2_profile.html", {
        "data": onboarding_data,
    })


@login_required
def onboarding_step3_connect(request: HttpRequest) -> HttpResponse:
    """Step 3: Connect LinkedIn account (enter credentials)."""
    onboarding_data = request.session.get("li_onboarding", {})
    if not onboarding_data.get("target_industry"):
        return redirect("linkedin:onboarding_step2")

    if request.method == "POST":
        email = request.POST.get("linkedin_email", "").strip()
        password = request.POST.get("linkedin_password", "").strip()

        if not email or not password:
            messages.error(request, "Please enter your LinkedIn email and password.")
            return redirect("linkedin:onboarding_step3")

        # Store credentials in PyRunner Secrets (encrypted)
        secret_key = f"LI_CREDENTIALS_{request.user.id}"
        credentials = {"email": email, "password": password}

        secret, created = Secret.objects.get_or_create(key=secret_key)
        secret.set_value(str(credentials))  # Fernet encrypted
        secret.description = f"LinkedIn credentials for {request.user.email}"
        secret.created_by = request.user
        secret.save()

        onboarding_data["credentials_secret_key"] = secret_key
        onboarding_data["linkedin_email"] = email  # Keep email for display
        request.session["li_onboarding"] = onboarding_data
        return redirect("linkedin:onboarding_step4")

    return render(request, "linkedin/onboarding/step3_connect.html", {
        "data": onboarding_data,
    })


@login_required
def onboarding_step4_strategy(request: HttpRequest) -> HttpResponse:
    """Step 4: Review strategy and activate."""
    onboarding_data = request.session.get("li_onboarding", {})
    if not onboarding_data.get("credentials_secret_key"):
        return redirect("linkedin:onboarding_step3")

    if request.method == "POST":
        # Create the LinkedInProfile
        profile = LinkedInProfile.objects.create(
            user=request.user,
            goal=onboarding_data["goal"],
            aggression=onboarding_data.get("aggression", "balanced"),
            target_industry=onboarding_data.get("target_industry", ""),
            target_role=onboarding_data.get("target_role", ""),
            target_location=onboarding_data.get("target_location", ""),
            skills=onboarding_data.get("skills", ""),
            bio_summary=onboarding_data.get("bio_summary", ""),
            credentials_secret_key=onboarding_data["credentials_secret_key"],
            brand_watermark_text=onboarding_data.get("brand_watermark_text", ""),
            datastore_name=f"li_{str(request.user.id)[:8]}_state",
            status=LinkedInProfile.Status.ACTIVE,
            post_days=[0, 2, 4],   # Default: Mon, Wed, Fri
            post_time="08:00",
            posts_per_week=3,
        )

        # Create DataStore for this user
        DataStore.objects.get_or_create(
            name=profile.datastore_name,
            defaults={
                "description": f"LinkedIn Strategist state for {request.user.email}",
                "created_by": request.user,
            }
        )

        # Provision PyRunner scripts for this user
        _provision_pyrunner_scripts(profile, request.user)

        # Clear session
        del request.session["li_onboarding"]

        messages.success(request, "Your LinkedIn Strategist is now active!")
        return redirect("linkedin:dashboard")

    # Preview the strategy
    strategy_preview = _build_strategy_preview(onboarding_data)

    return render(request, "linkedin/onboarding/step4_strategy.html", {
        "data": onboarding_data,
        "strategy": strategy_preview,
    })


def _build_strategy_preview(data: dict) -> dict:
    """Build a human-readable preview of what the system will do."""
    goal_actions = {
        "get_job": ["Post 3x/week about your expertise", "Apply to 10 jobs/day automatically",
                    "Connect with 20 recruiters/day", "Comment on industry posts"],
        "get_clients": ["Post 4x/week with case studies and insights", "Hunt potential clients",
                        "Send personalized connection requests", "Build your authority"],
        "build_brand": ["Post 5x/week across content types", "Comment on influencer posts",
                        "Grow connections strategically", "Track engagement growth"],
        "grow_business": ["Post thought leadership content", "Generate inbound leads",
                          "Build strategic partnerships", "Weekly performance reports"],
    }

    return {
        "actions": goal_actions.get(data.get("goal", ""), []),
        "posts_per_week": 3,
        "first_post_time": "Tomorrow at 8:00 AM",
    }


def _provision_pyrunner_scripts(profile: LinkedInProfile, user) -> None:
    """
    Create PyRunner Script and Schedule records for the user's LinkedIn modules.
    This wires the LinkedIn automation into PyRunner's task execution engine.
    """
    from core.models import Script, ScriptSchedule, Environment
    from core.services.schedule_service import ScheduleService

    # Get the default environment
    env = Environment.objects.filter(is_default=True).first()
    if not env:
        env = Environment.objects.filter(is_active=True).first()

    # Load script templates
    scripts_to_create = [
        {
            "name": f"[LI] Post Publisher — {user.email}",
            "file": "linkedin/scripts/post_publisher.py",
            "schedule_mode": "daily",
            "schedule_times": [profile.post_time],
            "active": profile.module_posting,
        },
        {
            "name": f"[LI] Commenter — {user.email}",
            "file": "linkedin/scripts/commenter.py",
            "schedule_mode": "daily",
            "schedule_times": ["09:00", "15:00"],
            "active": profile.module_commenting,
        },
        {
            "name": f"[LI] Connection Builder — {user.email}",
            "file": "linkedin/scripts/connection_builder.py",
            "schedule_mode": "daily",
            "schedule_times": ["10:00"],
            "active": profile.module_connecting,
        },
    ]

    if profile.module_job_applying:
        scripts_to_create.append({
            "name": f"[LI] Job Applier — {user.email}",
            "file": "linkedin/scripts/job_applier.py",
            "schedule_mode": "daily",
            "schedule_times": ["07:00"],
            "active": True,
        })

    for script_def in scripts_to_create:
        if not script_def["active"]:
            continue

        # Read script template code
        with open(script_def["file"]) as f:
            code = f.read()

        script = Script.objects.create(
            name=script_def["name"],
            code=code,
            environment=env,
            is_enabled=True,
            created_by=user,
            timeout_seconds=600,  # 10 minutes
        )

        schedule = ScriptSchedule.objects.create(
            script=script,
            run_mode="daily",
            daily_times=script_def["schedule_times"],
            timezone="UTC",
            is_active=True,
            created_by=user,
        )

        ScheduleService.sync_schedule(schedule)