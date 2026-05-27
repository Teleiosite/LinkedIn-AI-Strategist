import json
import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta

from billing.models import Plan, Subscription


def _get_stripe():
    """Return stripe with the API key configured. Called lazily inside views."""
    stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    return stripe



@login_required
def pricing_view(request):
    """Show pricing plans."""
    plans = Plan.objects.filter(is_active=True).order_by("price_monthly")
    return render(request, "billing/pricing.html", {"plans": plans})


@login_required
def checkout_success(request):
    """Show success page after Stripe checkout."""
    subscription = Subscription.objects.filter(user=request.user).first()
    return render(request, "billing/success.html", {"subscription": subscription})


@login_required
@require_POST
def create_checkout_session(request):
    """Create Stripe checkout session for a plan."""
    st = _get_stripe()
    plan_slug = request.POST.get("plan_slug")
    try:
        plan = Plan.objects.get(slug=plan_slug)
    except Plan.DoesNotExist:
        return JsonResponse({"error": "Invalid plan"}, status=400)

    session = st.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        customer_email=request.user.email,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=request.build_absolute_uri("/billing/success/"),
        cancel_url=request.build_absolute_uri("/billing/pricing/"),
        metadata={
            "user_id": str(request.user.id),
            "plan_slug": plan.slug,
        },
        subscription_data={
            "trial_period_days": 14,
        },
    )

    return JsonResponse({"checkout_url": session.url})


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks to update subscription status."""
    st = _get_stripe()
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = st.Webhook.construct_event(
            payload, sig_header, getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        _handle_checkout_completed(session)

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        _handle_subscription_updated(subscription)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        _handle_subscription_canceled(subscription)

    return HttpResponse(status=200)


def _handle_checkout_completed(session):
    """Create or update subscription after successful checkout."""
    from core.models import User
    user_id = session["metadata"].get("user_id")
    plan_slug = session["metadata"].get("plan_slug")

    try:
        user = User.objects.get(id=user_id)
        plan = Plan.objects.get(slug=plan_slug)
    except (User.DoesNotExist, Plan.DoesNotExist):
        return

    Subscription.objects.update_or_create(
        user=user,
        defaults={
            "plan": plan,
            "stripe_customer_id": session.get("customer", ""),
            "stripe_subscription_id": session.get("subscription", ""),
            "status": Subscription.Status.TRIALING,
            "trial_ends_at": timezone.now() + timedelta(days=14),
        }
    )


def _handle_subscription_updated(stripe_sub):
    try:
        sub = Subscription.objects.get(
            stripe_subscription_id=stripe_sub["id"]
        )
        sub.status = stripe_sub["status"]
        sub.save(update_fields=["status", "updated_at"])
    except Subscription.DoesNotExist:
        pass


def _handle_subscription_canceled(stripe_sub):
    try:
        sub = Subscription.objects.get(
            stripe_subscription_id=stripe_sub["id"]
        )
        sub.status = Subscription.Status.CANCELED
        sub.canceled_at = timezone.now()
        sub.save()
    except Subscription.DoesNotExist:
        pass