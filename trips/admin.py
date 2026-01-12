from django.contrib import admin

from .models import (
    Day,
    Experience,
    Link,
    Meal,
    SimpleTransfer,
    Stay,
    StayTransfer,
    Transport,
    Trip,
)


@admin.register(Trip)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "author"]


admin.site.register(Link)


@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = ["__str__", "trip", "date"]


@admin.register(Transport)
class TransportAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(SimpleTransfer)
class SimpleTransferAdmin(admin.ModelAdmin):
    list_display = ["__str__", "day", "transport_mode"]


@admin.register(StayTransfer)
class StayTransferAdmin(admin.ModelAdmin):
    list_display = ["__str__", "from_day", "to_day", "transport_mode"]


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(Stay)
class StayAdmin(admin.ModelAdmin):
    list_display = ["__str__"]
