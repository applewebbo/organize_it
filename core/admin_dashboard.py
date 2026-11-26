from django.contrib import admin
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from accounts.models import CustomUser, Profile
from trips.models import Trip


class AdminStatsDashboardView(TemplateView):
    """Aggregate, anonymized usage statistics dashboard for staff admins."""

    template_name = "admin/stats_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(admin.site.each_context(self.request))
        context["title"] = _("Usage Statistics")

        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()

        new_users_qs = (
            CustomUser.objects.annotate(month=TruncMonth("date_joined"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        new_users_per_month = [
            {"month": row["month"].strftime("%Y-%m"), "count": row["count"]}
            for row in new_users_qs
            if row["month"] is not None
        ]

        total_trips = Trip.objects.count()
        trips_qs = (
            Trip.objects.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        trips_per_month = [
            {"month": row["month"].strftime("%Y-%m"), "count": row["count"]}
            for row in trips_qs
            if row["month"] is not None
        ]

        status_labels = dict(Trip.Status.choices)
        trips_status_qs = (
            Trip.objects.values("status").annotate(count=Count("id")).order_by("status")
        )
        trips_by_status = [
            {
                "status": row["status"],
                "label": str(status_labels.get(row["status"], row["status"])),
                "count": row["count"],
            }
            for row in trips_status_qs
        ]

        ai_stats = Profile.objects.aggregate(
            total=Count("id"),
            enabled=Count("id", filter=Q(ai_suggestions_enabled=True)),
        )
        ai_total_profiles = ai_stats["total"]
        ai_enabled_count = ai_stats["enabled"]
        ai_adoption_rate = (
            round((ai_enabled_count / ai_total_profiles) * 100, 1)
            if ai_total_profiles
            else 0.0
        )

        context.update(
            {
                "total_users": total_users,
                "active_users": active_users,
                "new_users_per_month": new_users_per_month,
                "total_trips": total_trips,
                "trips_per_month": trips_per_month,
                "trips_by_status": trips_by_status,
                "ai_total_profiles": ai_total_profiles,
                "ai_enabled_count": ai_enabled_count,
                "ai_adoption_rate": ai_adoption_rate,
                "chart_data": {
                    "new_users_per_month": {
                        "labels": [item["month"] for item in new_users_per_month],
                        "counts": [item["count"] for item in new_users_per_month],
                    },
                    "trips_per_month": {
                        "labels": [item["month"] for item in trips_per_month],
                        "counts": [item["count"] for item in trips_per_month],
                    },
                    "trips_by_status": {
                        "labels": [item["label"] for item in trips_by_status],
                        "counts": [item["count"] for item in trips_by_status],
                    },
                },
            }
        )
        return context
