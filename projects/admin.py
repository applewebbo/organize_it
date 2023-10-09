from django.contrib import admin

from .models import Link, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass


admin.site.register(Link)
