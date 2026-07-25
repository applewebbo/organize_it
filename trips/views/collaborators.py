import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override as translation_override
from django.views.decorators.http import require_http_methods

from trips.forms import NamedParticipantForm, ShareLinkCreateForm
from trips.models import ShareLink, TripCollaboration, TripInvitation
from trips.utils import get_trip_for_owner_or_404, get_trip_or_404

logger = logging.getLogger(__name__)


def share_link_create(request, trip_id):
    """Create a new share link for a trip (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)

    created_link = None
    if request.method == "POST":
        form = ShareLinkCreateForm(request.POST)
        if form.is_valid():
            created_link = form.save(trip=trip, created_by=request.user)
            form = ShareLinkCreateForm()
    else:
        form = ShareLinkCreateForm()

    links = trip.share_links.filter(is_active=True).order_by("-created_at")
    return TemplateResponse(
        request,
        "trips/share-link-modal.html",
        {"form": form, "trip": trip, "links": links, "created_link": created_link},
    )


def share_link_list(request, trip_id):
    """List active share links for a trip (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    links = trip.share_links.filter(is_active=True).order_by("-created_at")
    return TemplateResponse(
        request,
        "trips/share-link-list.html",
        {"trip": trip, "links": links},
    )


@require_http_methods(["POST"])
def share_link_revoke(request, link_id):
    """Deactivate a share link (owner only)."""
    link = get_object_or_404(ShareLink, id=link_id, trip__author=request.user)
    link.is_active = False
    link.save(update_fields=["is_active"])
    trip = link.trip
    links = trip.share_links.filter(is_active=True).order_by("-created_at")
    return TemplateResponse(
        request,
        "trips/share-link-modal.html",
        {
            "form": ShareLinkCreateForm(),
            "trip": trip,
            "links": links,
            "created_link": None,
        },
    )


def search_user_by_email(request, trip_id):
    """HTMX: search registered user by email to invite as collaborator (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    email = request.GET.get("collab_email", "").strip()
    User = get_user_model()

    if not email:
        return HttpResponse("")

    existing_ids = set(trip.collaborators.values_list("id", flat=True))
    existing_ids.add(trip.author_id)

    # Use partial matching (case-insensitive) for email search
    matching_users = User.objects.filter(email__icontains=email)[:10]

    results = []
    for user in matching_users:
        already_collab = user.id in existing_ids
        results.append(
            {
                "user": user,
                "already_collab": already_collab,
            }
        )

    return TemplateResponse(
        request,
        "trips/includes/collab-search-result.html",
        {"trip": trip, "results": results, "email": email},
    )


@require_http_methods(["POST"])
def add_collaborator(request, trip_id):
    """Add a registered user as collaborator (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    User = get_user_model()
    email = request.POST.get("email", "").strip()
    can_edit = request.POST.get("can_edit", "true").lower() != "false"

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return HttpResponse(status=400)

    if user == trip.author or trip.collaborators.filter(pk=user.pk).exists():
        return HttpResponse(status=400)

    color = TripCollaboration.next_free_color(trip)
    TripCollaboration.objects.create(
        trip=trip, user=user, color=color, added_by=request.user, can_edit=can_edit
    )

    trip_url = request.build_absolute_uri(reverse("trips:trip-detail", args=[trip.pk]))
    context = {"trip": trip, "added_by": request.user, "trip_url": trip_url}
    recipient_language = getattr(user.profile, "language", "it")
    with translation_override(recipient_language):
        subject = render_to_string(
            "trips/email/added_as_collaborator_subject.txt", context
        ).strip()
        text_body = render_to_string(
            "trips/email/added_as_collaborator_body.txt", context
        )
        html_body = render_to_string(
            "trips/email/added_as_collaborator_body.html", context
        )
    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[user.email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal-list.html",
        {"trip": trip, "collaborations": collaborations},
        headers={"HX-Trigger": "collaboratorsModified"},
    )


@require_http_methods(["POST"])
def toggle_participant_role(request, trip_id, collaboration_id):
    """Downgrade editor to viewer (owner only). Upgrade is not allowed via this view."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    collaboration = get_object_or_404(TripCollaboration, pk=collaboration_id, trip=trip)
    if not collaboration.can_edit:
        return HttpResponse(status=400)
    collaboration.can_edit = False
    collaboration.save()
    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal-list.html",
        {"trip": trip, "collaborations": collaborations},
        headers={"HX-Trigger": "collaboratorsModified"},
    )


@require_http_methods(["POST"])
def add_viewer_by_email(request, trip_id):
    """Add a viewer by email — sends a permanent share link (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    User = get_user_model()
    email = request.POST.get("email", "").strip()

    if not email:
        return HttpResponse(status=400)

    if trip.collaborations.filter(participant_email=email).exists():
        return HttpResponse(status=400)

    share_link = ShareLink.objects.create(
        trip=trip,
        created_by=request.user,
        permission_level=ShareLink.PermissionLevel.VIEW,
        expires_at=None,
        label=email,
    )

    color = TripCollaboration.next_free_color(trip)
    try:
        user = User.objects.get(email=email)
        if trip.collaborators.filter(pk=user.pk).exists() or user == trip.author:
            share_link.delete()
            return HttpResponse(status=400)
        TripCollaboration.objects.create(
            trip=trip,
            user=user,
            color=color,
            added_by=request.user,
            can_edit=False,
            share_link=share_link,
        )
    except User.DoesNotExist:
        TripCollaboration.objects.create(
            trip=trip,
            user=None,
            participant_email=email,
            color=color,
            added_by=request.user,
            can_edit=False,
            share_link=share_link,
        )

    share_url = request.build_absolute_uri(share_link.get_absolute_url())
    context = {"trip": trip, "invited_by": request.user, "share_url": share_url}
    sender_language = getattr(request.user.profile, "language", "it")
    with translation_override(sender_language):
        subject = render_to_string(
            "trips/email/viewer_invitation_subject.txt", context
        ).strip()
        text_body = render_to_string("trips/email/viewer_invitation_body.txt", context)
        html_body = render_to_string("trips/email/viewer_invitation_body.html", context)
    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal-list.html",
        {"trip": trip, "collaborations": collaborations},
        headers={"HX-Trigger": "collaboratorsModified"},
    )


@require_http_methods(["POST"])
def add_named_participant(request, trip_id):
    """Add a named participant with no account or email (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    form = NamedParticipantForm(request.POST)

    if not form.is_valid():
        return HttpResponse(status=400)

    color = TripCollaboration.next_free_color(trip)
    TripCollaboration.objects.create(
        trip=trip,
        user=None,
        participant_name=form.cleaned_data["name"],
        is_child=form.cleaned_data["is_child"],
        age=form.cleaned_data["age"],
        color=color,
        added_by=request.user,
        can_edit=False,
    )

    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal-list.html",
        {"trip": trip, "collaborations": collaborations},
        headers={"HX-Trigger": "collaboratorsModified"},
    )


@require_http_methods(["POST"])
def remove_collaborator(request, trip_id, collaboration_id):
    """Remove a collaborator from a trip (owner only, data is preserved)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    collaboration = get_object_or_404(TripCollaboration, pk=collaboration_id, trip=trip)
    collaboration.delete()

    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal-list.html",
        {"trip": trip, "collaborations": collaborations},
        headers={"HX-Trigger": "collaboratorsModified"},
    )


def collaborators_modal(request, trip_id):
    """GET: render the collaborators management modal (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal.html",
        {"trip": trip, "collaborations": collaborations},
    )


def collab_inline(request, trip_id):
    """GET: render the compact inline collaborators row (HTMX refresh)."""
    trip = get_trip_or_404(trip_id, request.user)
    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-inline.html",
        {"trip": trip, "collaborations": collaborations},
    )


@require_http_methods(["POST"])
def invite_collaborator(request, trip_id):
    """Invite a non-registered user by email (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    User = get_user_model()
    email = request.POST.get("email", "").strip()

    if User.objects.filter(email=email).exists():
        return HttpResponse(status=400)

    invitation = TripInvitation.objects.create(
        trip=trip,
        email=email,
        invited_by=request.user,
        expires_at=timezone.now() + timezone.timedelta(days=7),
    )

    accept_url = request.build_absolute_uri(invitation.get_absolute_url())
    context = {"trip": trip, "invited_by": request.user, "accept_url": accept_url}
    sender_language = getattr(request.user.profile, "language", "it")
    with translation_override(sender_language):
        subject = render_to_string(
            "trips/email/invitation_subject.txt", context
        ).strip()
        text_body = render_to_string("trips/email/invitation_body.txt", context)
        html_body = render_to_string("trips/email/invitation_body.html", context)
    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    return TemplateResponse(
        request,
        "trips/includes/collab-invite-sent.html",
        {"email": email},
    )


@login_not_required
def accept_invitation(request, token):
    """Accept a trip collaboration invitation via token."""
    invitation = get_object_or_404(TripInvitation, token=token)

    if not invitation.is_valid:
        return HttpResponse(status=400)

    if not request.user.is_authenticated:
        signup_url = reverse("account_signup")
        accept_url = reverse("trips:accept-invitation", kwargs={"token": token})
        request.session["invitation_token"] = str(token)
        return redirect(f"{signup_url}?next={accept_url}")

    invitation.is_accepted = True
    invitation.accepted_at = timezone.now()
    invitation.save()

    trip = invitation.trip
    color = TripCollaboration.next_free_color(trip)
    TripCollaboration.objects.get_or_create(
        trip=trip,
        user=request.user,
        defaults={"color": color, "added_by": invitation.invited_by, "can_edit": False},
    )

    trip_url = request.build_absolute_uri(reverse("trips:trip-detail", args=[trip.pk]))
    context = {
        "trip": trip,
        "new_collaborator_email": request.user.email,
        "trip_url": trip_url,
    }
    owner_language = getattr(invitation.invited_by.profile, "language", "it")
    with translation_override(owner_language):
        subject = render_to_string(
            "trips/email/invitation_accepted_subject.txt", context
        ).strip()
        text_body = render_to_string(
            "trips/email/invitation_accepted_body.txt", context
        )
        html_body = render_to_string(
            "trips/email/invitation_accepted_body.html", context
        )
    msg = EmailMultiAlternatives(
        subject=subject, body=text_body, to=[invitation.invited_by.email]
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    messages.success(request, _("You've joined the trip as a participant."))
    return redirect(reverse("trips:trip-detail", args=[trip.pk]))
