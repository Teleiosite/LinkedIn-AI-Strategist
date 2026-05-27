from django.urls import path
from billing import views

app_name = "billing"

urlpatterns = [
    path("pricing/", views.pricing_view, name="pricing"),
    path("checkout/", views.create_checkout_session, name="checkout"),
    path("success/", views.checkout_success, name="success"),
    path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
]
