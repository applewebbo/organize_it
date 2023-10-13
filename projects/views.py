from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProjectForm
from .models import Project


def home(request):
    context = {}
    return render(request, "projects/index.html", context)


def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    context = {"project": project}
    return render(request, "projects/project-detail.html", context)


def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.author = request.user
            project.save()
            return redirect("projects:home")
    else:
        form = ProjectForm()
    context = {"form": form}
    return render(request, "projects/project-create.html", context)
