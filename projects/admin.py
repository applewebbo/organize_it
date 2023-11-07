from django.contrib import admin

from .models import Link, Note, Place, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass


admin.site.register(Link)
admin.site.register(Place)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    pass
