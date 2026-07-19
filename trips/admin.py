from django.contrib import admin

from .models import (
    Day,
    Expense,
    ExpenseParticipant,
    ExpenseShare,
    Experience,
    FamilyUnit,
    Link,
    Meal,
    Stay,
    Trip,
)


@admin.register(Trip)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "author"]


admin.site.register(Link)


@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "trip",
        "date",
        "destination",
        "destination_latitude",
        "destination_longitude",
        "transfer_duration_from_prev",
        "transfer_distance_from_prev",
    ]
    search_fields = ["destination", "trip__title"]
    list_filter = ["trip"]


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(Stay)
class StayAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(FamilyUnit)
class FamilyUnitAdmin(admin.ModelAdmin):
    list_display = ["__str__", "trip", "shared_wallet"]
    list_filter = ["trip"]


@admin.register(ExpenseParticipant)
class ExpenseParticipantAdmin(admin.ModelAdmin):
    list_display = ["__str__", "trip", "family_unit", "is_child", "is_active"]
    list_filter = ["trip", "is_child", "is_active"]


class ExpenseShareInline(admin.TabularInline):
    model = ExpenseShare
    extra = 0


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["title", "trip", "amount", "date", "payer"]
    list_filter = ["trip"]
    inlines = [ExpenseShareInline]
