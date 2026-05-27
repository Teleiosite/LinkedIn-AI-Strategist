import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.utils import timezone

from linkedin.models import LinkedInProfile, GeneratedPost
from linkedin.services.content_service import ContentService
from linkedin.services.image_service import ImageService
from linkedin.services.strategy_service import StrategyService

logger = logging.getLogger(__name__)


@login_required
def content_queue_view(request: HttpRequest) -> HttpResponse:
    """View content queue: drafts, scheduled, approved, posted."""
    try:
        profile = request.user.linkedin_profile
    except LinkedInProfile.DoesNotExist:
        return redirect("linkedin:onboarding_step1")

    posts = GeneratedPost.objects.filter(profile=profile).order_by("-created_at")
    drafts = posts.filter(status=GeneratedPost.Status.DRAFT)
    approved = posts.filter(status=GeneratedPost.Status.APPROVED)
    posted = posts.filter(status=GeneratedPost.Status.POSTED)
    failed = posts.filter(status=GeneratedPost.Status.FAILED)

    return render(request, "linkedin/content/queue.html", {
        "profile": profile,
        "drafts": drafts,
        "approved": approved,
        "posted": posted,
        "failed": failed,
    })


@login_required
def post_preview_view(request: HttpRequest, pk) -> HttpResponse:
    """Preview a generated post with its image."""
    try:
        profile = request.user.linkedin_profile
    except LinkedInProfile.DoesNotExist:
        return redirect("linkedin:onboarding_step1")

    post = get_object_or_404(GeneratedPost, pk=pk, profile=profile)
    return render(request, "linkedin/content/post_preview.html", {
        "profile": profile,
        "post": post,
    })


@login_required
def approve_post_view(request: HttpRequest, pk) -> HttpResponse:
    """Approve a draft post so it can be published."""
    try:
        profile = request.user.linkedin_profile
    except LinkedInProfile.DoesNotExist:
        return redirect("linkedin:onboarding_step1")

    post = get_object_or_404(GeneratedPost, pk=pk, profile=profile)
    post.status = GeneratedPost.Status.APPROVED
    post.save()
    messages.success(request, "Post approved! It is now scheduled for publication.")
    return redirect("linkedin:content_queue")


@login_required
def reject_post_view(request: HttpRequest, pk) -> HttpResponse:
    """Reject a draft post."""
    try:
        profile = request.user.linkedin_profile
    except LinkedInProfile.DoesNotExist:
        return redirect("linkedin:onboarding_step1")

    post = get_object_or_404(GeneratedPost, pk=pk, profile=profile)
    post.status = GeneratedPost.Status.REJECTED
    post.save()
    messages.info(request, "Post rejected and moved out of queue.")
    return redirect("linkedin:content_queue")


@login_required
def generate_post_now_view(request: HttpRequest) -> HttpResponse:
    """Generate a post immediately using the AI services."""
    try:
        profile = request.user.linkedin_profile
    except LinkedInProfile.DoesNotExist:
        return redirect("linkedin:onboarding_step1")

    if request.method == "POST":
        # Call AI services to generate text + image
        content_svc = ContentService()
        image_svc = ImageService()

        # Determine type based on strategy
        plan = StrategyService.get_today_plan(profile)
        post_type = plan["post_type"]

        messages.info(request, f"Starting AI generation for a new '{post_type}' post...")
        try:
            # Step 1: Text
            post_data = content_svc.generate_post(profile, post_type)
            post_text = post_data["post_text"]
            hashtags = post_data.get("hashtags", "")
            full_text = f"{post_text}\n\n{hashtags}"

            # Step 2: Image brief & generation
            visual_brief = content_svc.generate_visual_brief(post_text, post_type)
            image_data = image_svc.generate_for_post(
                profile=profile,
                post_text=post_text,
                post_type=post_type,
                visual_brief=visual_brief
            )

            # Save
            GeneratedPost.objects.create(
                profile=profile,
                post_type=post_type,
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
                text_model_used=post_data.get("model", ""),
                image_model_used=image_data.get("image_model_used", ""),
                text_provider=post_data.get("provider", ""),
                image_provider=image_data.get("image_provider", ""),
                generation_cost_usd=post_data.get("cost_usd", 0) + image_data.get("cost_usd", 0),
                status=GeneratedPost.Status.DRAFT,  # Set to draft so user reviews it
            )
            messages.success(request, "New AI post and custom matching visual generated successfully!")
        except Exception as e:
            logger.exception("AI Generation failed")
            messages.error(request, f"AI generation failed: {e}")

    return redirect("linkedin:content_queue")
