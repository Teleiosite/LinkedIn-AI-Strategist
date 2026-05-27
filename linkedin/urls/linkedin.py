from django.urls import path
from linkedin.views import onboarding, dashboard, content

app_name = "linkedin"

urlpatterns = [
    # Onboarding
    path("setup/", onboarding.onboarding_step1_goal, name="onboarding_step1"),
    path("setup/profile/", onboarding.onboarding_step2_profile, name="onboarding_step2"),
    path("setup/connect/", onboarding.onboarding_step3_connect, name="onboarding_step3"),
    path("setup/strategy/", onboarding.onboarding_step4_strategy, name="onboarding_step4"),

    # Dashboard
    path("", dashboard.dashboard_view, name="dashboard"),

    # Content
    path("content/", content.content_queue_view, name="content_queue"),
    path("content/<uuid:pk>/preview/", content.post_preview_view, name="post_preview"),
    path("content/<uuid:pk>/approve/", content.approve_post_view, name="approve_post"),
    path("content/<uuid:pk>/reject/", content.reject_post_view, name="reject_post"),
]