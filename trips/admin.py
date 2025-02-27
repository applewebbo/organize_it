from django.contrib import admin

from .models import Day, Experience, Link, Meal, Note, Stay, Transport, Trip


@admin.register(Trip)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "author"]
    exclude = ["status"]


admin.site.register(Link)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    pass


@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = ["__str__", "trip", "date"]


@admin.register(Transport)
class TransportAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(Stay)
class StayAdmin(admin.ModelAdmin):
    list_display = ["__str__"]
