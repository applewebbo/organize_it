from django.shortcuts import get_object_or_404, render

from .models import Project


def home(request):
    context = {}
    return render(request, "projects/index.html", context)


def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    context = {"project": project}
    return render(request, "projects/project-detail.html", context)
