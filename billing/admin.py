from django.contrib import admin
from billing.models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price_monthly", "is_active", "sort_order"]
    list_filter = ["is_active"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "status", "trial_ends_at", "created_at"]
    list_filter = ["status", "plan"]
    search_fields = ["user__email", "stripe_customer_id"]
    readonly_fields = ["id", "created_at", "updated_at"]
