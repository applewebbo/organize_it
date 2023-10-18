from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .forms import ProjectForm
from .models import Project


def home(request):
    user = request.user
    if user.is_authenticated:
        projects = Project.objects.filter(author=request.user)
    else:
        projects = None
    context = {"projects": projects}
    return render(request, "projects/index.html", context)


@login_required
def project_list(request):
    projects = Project.objects.filter(author=request.user)
    context = {"projects": projects}
    return render(request, "projects/index.html#project-list", context)


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    context = {"project": project}
    return render(request, "projects/project-detail.html", context)


@login_required
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.author = request.user
            project.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                f"<strong>{project.title}</strong> added successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "projectSaved"})

    form = ProjectForm()
    context = {"form": form}
    return render(request, "projects/project-create.html", context)


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        f"<strong>{project.title}</strong> deleted successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "projectSaved"},
    )


@login_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                f"<strong>{project.title}</strong> added successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "projectSaved"})

    form = ProjectForm(instance=project)
    context = {"form": form}
    return render(request, "projects/project-create.html", context)
