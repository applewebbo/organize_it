from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .forms import LinkForm, PlaceForm, ProjectForm
from .models import Link, Place, Project


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
    qs = Project.objects.prefetch_related("links", "places")
    project = get_object_or_404(qs, pk=pk)
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
                f"<strong>{project.title}</strong> updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "projectSaved"})

    form = ProjectForm(instance=project)
    context = {"form": form}
    return render(request, "projects/project-create.html", context)


@login_required
def project_add_link(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        form = LinkForm(request.POST)
        if form.is_valid():
            link = form.save(commit=False)
            link.author = request.user
            link.save()
            project.links.add(link)
            project.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Link added successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "linkSaved"})

    form = LinkForm()
    context = {"form": form}
    return render(request, "projects/link-create.html", context)


@login_required
def link_delete(request, pk):
    link = get_object_or_404(Link, pk=pk)
    link.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        "Link deleted successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "linkSaved"},
    )


@login_required
def link_update(request, pk):
    link = get_object_or_404(Link, pk=pk)

    if request.method == "POST":
        form = LinkForm(request.POST, instance=link)
        if form.is_valid():
            link = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Link updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "linkSaved"})

    form = LinkForm(instance=link)
    context = {"form": form}
    return render(request, "projects/link-create.html", context)


@login_required
def link_list(request, project_id):
    links = Link.objects.filter(projects=project_id)
    project = get_object_or_404(Project, pk=project_id)
    context = {"links": links, "project": project}
    return render(request, "projects/project-detail.html#link-list", context)


@login_required
def place_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if request.method == "POST":
        form = PlaceForm(request.POST)
        if form.is_valid():
            place = form.save(commit=False)
            place.project = project
            place.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                f"<strong>{place.name}</strong> added successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "placeSaved"})
    form = PlaceForm()
    context = {"form": form}
    return render(request, "projects/place-create.html", context)


@login_required
def place_list(request, project_id):
    places = Place.objects.filter(project=project_id)
    project = get_object_or_404(Project, pk=project_id)
    context = {"places": places, "project": project}
    return render(request, "projects/project-detail.html#place-list", context)


@login_required
def place_delete(request, pk):
    place = get_object_or_404(Place, pk=pk)
    place.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        "Place deleted successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "placeSaved"},
    )


@login_required
def place_update(request, pk):
    place = get_object_or_404(Place, pk=pk)

    if request.method == "POST":
        form = PlaceForm(request.POST, instance=place)
        if form.is_valid():
            place = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Place updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "placeSaved"})

    form = PlaceForm(instance=place)
    context = {"form": form}
    return render(request, "projects/place-create.html", context)
