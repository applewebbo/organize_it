from django.contrib import admin

from .models import Day, Link, Note, Place, Transport, Trip


@admin.register(Trip)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "author"]
    exclude = ["status"]


admin.site.register(Link)
admin.site.register(Place)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    pass


@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = ["__str__", "trip", "date"]


@admin.register(Transport)
class TransportAdmin(admin.ModelAdmin):
    list_display = ["__str__"]
