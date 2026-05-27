from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib import messages

from linkedin.models import LinkedInProfile, GeneratedPost, JobApplication, Lead


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """Dashboard showing stats, toggles, and recent activity."""
    try:
        profile = request.user.linkedin_profile
    except LinkedInProfile.DoesNotExist:
        # If no profile, redirect to step 1 of onboarding wizard
        return redirect("linkedin:onboarding_step1")

    # Aggregate stats
    posts = GeneratedPost.objects.filter(profile=profile)
    total_posts = posts.count()
    posted_posts = posts.filter(status=GeneratedPost.Status.POSTED).count()
    drafts_count = posts.filter(status=GeneratedPost.Status.DRAFT).count()
    leads_count = Lead.objects.filter(profile=profile).count()
    apps_count = JobApplication.objects.filter(profile=profile).count()

    # Get recent objects for display
    recent_posts = posts.order_by("-created_at")[:5]
    recent_leads = Lead.objects.filter(profile=profile).order_by("-identified_at")[:5]
    recent_apps = JobApplication.objects.filter(profile=profile).order_by("-applied_at")[:5]

    # Handle toggling module options via POST
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_modules":
            profile.module_posting = request.POST.get("module_posting") == "on"
            profile.module_commenting = request.POST.get("module_commenting") == "on"
            profile.module_connecting = request.POST.get("module_connecting") == "on"
            profile.module_job_applying = request.POST.get("module_job_applying") == "on"
            profile.module_client_hunting = request.POST.get("module_client_hunting") == "on"
            profile.save()
            messages.success(request, "Modules updated successfully!")
            return redirect("linkedin:dashboard")

    return render(request, "linkedin/dashboard.html", {
        "profile": profile,
        "total_posts": total_posts,
        "posted_posts": posted_posts,
        "drafts_count": drafts_count,
        "leads_count": leads_count,
        "apps_count": apps_count,
        "recent_posts": recent_posts,
        "recent_leads": recent_leads,
        "recent_apps": recent_apps,
    })
