from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from .forms import LinkForm, NoteForm, PlaceForm, ProjectDateUpdateForm, ProjectForm
from .models import Link, Note, Place, Project


def calculate_bounds(locations):
    # Check if the list is not empty
    if not locations:
        return None

    sw = list(min((point["latitude"], point["longitude"]) for point in locations))
    ne = list(max((point["latitude"], point["longitude"]) for point in locations))

    return [sw, ne]


def home(request):
    user = request.user
    if user.is_authenticated:
        projects = Project.objects.filter(author=request.user)
    else:
        projects = None
    context = {"projects": projects}
    return TemplateResponse(request, "projects/index.html", context)


@login_required
def project_list(request):
    if request.htmx:
        template = "projects/project-list.html#project-list"
    else:
        template = "projects/project-list.html"
    active_projects = Project.objects.filter(author=request.user).exclude(status=5)
    archived_projects = Project.objects.filter(author=request.user, status=5)
    context = {
        "active_projects": active_projects,
        "archived_projects": archived_projects,
    }
    return TemplateResponse(request, template, context)


@login_required
def project_detail(request, pk):
    qs = Project.objects.prefetch_related("links", "places", "notes")
    project = get_object_or_404(qs, pk=pk)

    locations = list(Place.objects.filter(project=pk).values("latitude", "longitude"))
    map_bounds = calculate_bounds(locations)

    context = {
        "project": project,
        "locations": locations,
        "map_bounds": map_bounds,
    }
    return TemplateResponse(request, "projects/project-detail.html", context)


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
    return TemplateResponse(request, "projects/project-create.html", context)


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
        form = ProjectForm(request.POST, instance=project)
        context = {"form": form}
        return TemplateResponse(request, "projects/project-create.html", context)

    form = ProjectForm(instance=project)
    context = {"form": form}
    return TemplateResponse(request, "projects/project-create.html", context)


def project_archive(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.status = 5
    project.save()
    messages.add_message(
        request,
        messages.SUCCESS,
        f"<strong>{project.title}</strong> archived successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "projectSaved"},
    )


def project_dates_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        form = ProjectDateUpdateForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Dates updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "projectSaved"})
        form = ProjectDateUpdateForm(request.POST, instance=project)
        context = {"form": form}
        return TemplateResponse(request, "projects/project-dates-update.html", context)

    form = ProjectDateUpdateForm(instance=project)
    context = {"form": form}
    return TemplateResponse(request, "projects/project-dates-update.html", context)


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
    return TemplateResponse(request, "projects/link-create.html", context)


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
    return TemplateResponse(request, "projects/link-create.html", context)


@login_required
def link_list(request, pk):
    links = Link.objects.filter(projects=pk)
    project = get_object_or_404(Project, pk=pk)
    context = {"links": links, "project": project}
    return TemplateResponse(request, "projects/project-detail.html#link-list", context)


@login_required
def project_add_place(request, pk):
    project = get_object_or_404(Project, pk=pk)
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
    return TemplateResponse(request, "projects/place-create.html", context)


@login_required
def place_list(request, pk):
    places = Place.objects.filter(project=pk)
    project = get_object_or_404(Project, pk=pk)
    locations = list(places.values("latitude", "longitude"))
    map_bounds = calculate_bounds(locations)
    context = {
        "places": places,
        "project": project,
        "locations": locations,
        "map_bounds": map_bounds,
    }
    return TemplateResponse(request, "projects/project-detail.html#place-list", context)


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
    return TemplateResponse(request, "projects/place-create.html", context)


@login_required
def project_add_note(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if request.method == "POST":
        form = NoteForm(project, request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.project = project
            note.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Note added successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "noteSaved"})

        form = NoteForm(project, request.POST)
        context = {"form": form}
        return TemplateResponse(request, "projects/note-create.html", context)

    form = NoteForm(project)
    context = {"form": form}
    return TemplateResponse(request, "projects/note-create.html", context)


@login_required
def note_update(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.method == "POST":
        form = NoteForm(note.project, request.POST, instance=note)
        if form.is_valid():
            note = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Note updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "noteSaved"})

        form = NoteForm(note.project, instance=note)
        context = {"form": form}
        return TemplateResponse(request, "projects/note-create.html", context)

    form = NoteForm(note.project, instance=note)
    context = {"form": form}
    return TemplateResponse(request, "projects/note-create.html", context)


@login_required
def note_list(request, pk):
    notes = Note.objects.filter(project=pk)
    project = get_object_or_404(Project, pk=pk)
    context = {"notes": notes, "project": project}
    return TemplateResponse(request, "projects/project-detail.html#note-list", context)


@login_required
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk)
    note.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        "Note deleted successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "noteSaved"},
    )


@login_required
def note_check_or_uncheck(request, pk):
    note = get_object_or_404(Note, pk=pk)
    note.checked = not note.checked
    note.save()
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "noteSaved"},
    )
