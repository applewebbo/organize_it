from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from unfold.admin import ModelAdmin

from .forms import (
    AdminEmailForm,
    AdminNotificationForm,
    CustomUserChangeForm,
    CustomUserCreationForm,
    ProfileUpdateForm,
)
from .models import CustomUser, Notification, Profile


@admin.register(CustomUser)
class CustomUserAdmin(ModelAdmin, UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    actions = [
        "block_users",
        "unblock_users",
        "send_notification_action",
        "send_email_action",
    ]
    list_display = (
        "email",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "email",
        "is_staff",
        "is_active",
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Permissions",
            {"fields": ("is_staff", "is_active", "groups", "user_permissions")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)

    def get_urls(self):
        custom_urls = [
            path(
                "send-notification/",
                self.admin_site.admin_view(self.send_notification_view),
                name="accounts_customuser_send_notification",
            ),
            path(
                "send-email/",
                self.admin_site.admin_view(self.send_email_view),
                name="accounts_customuser_send_email",
            ),
        ]
        return custom_urls + super().get_urls()

    @admin.action(description=_("Block selected users"))
    def block_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            ngettext(
                "%d user blocked.",
                "%d users blocked.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description=_("Unblock selected users"))
    def unblock_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            ngettext(
                "%d user unblocked.",
                "%d users unblocked.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description=_("Send notification to selected users"))
    def send_notification_action(self, request, queryset):
        request.session["admin_selected_user_ids"] = list(
            queryset.values_list("pk", flat=True)
        )
        return redirect(reverse("admin:accounts_customuser_send_notification"))

    @admin.action(description=_("Send email to selected users"))
    def send_email_action(self, request, queryset):
        request.session["admin_selected_user_ids"] = list(
            queryset.values_list("pk", flat=True)
        )
        return redirect(reverse("admin:accounts_customuser_send_email"))

    def _get_selected_users(self, request):
        user_ids = request.session.get("admin_selected_user_ids", [])
        return CustomUser.objects.filter(pk__in=user_ids).order_by("email")

    def send_notification_view(self, request):
        users = self._get_selected_users(request)
        if not users.exists():
            self.message_user(
                request,
                _("No users selected."),
                messages.WARNING,
            )
            return redirect(reverse("admin:accounts_customuser_changelist"))

        form = AdminNotificationForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            message_text = form.cleaned_data["message"]
            notifications = [
                Notification(
                    recipient=user,
                    message=message_text,
                    created_by=request.user,
                )
                for user in users
            ]
            Notification.objects.bulk_create(notifications)
            request.session.pop("admin_selected_user_ids", None)
            count = len(notifications)
            self.message_user(
                request,
                ngettext(
                    "Notification sent to %d user.",
                    "Notification sent to %d users.",
                    count,
                )
                % count,
                messages.SUCCESS,
            )
            return redirect(reverse("admin:accounts_customuser_changelist"))

        context = {
            **self.admin_site.each_context(request),
            "title": _("Send notification"),
            "form": form,
            "users": users,
        }
        return TemplateResponse(
            request, "admin/accounts/send_notification.html", context
        )

    def send_email_view(self, request):
        users = self._get_selected_users(request)
        if not users.exists():
            self.message_user(
                request,
                _("No users selected."),
                messages.WARNING,
            )
            return redirect(reverse("admin:accounts_customuser_changelist"))

        form = AdminEmailForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            subject = form.cleaned_data["subject"]
            body = form.cleaned_data["body"]
            recipient_emails = list(users.values_list("email", flat=True))
            for email in recipient_emails:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                )
            request.session.pop("admin_selected_user_ids", None)
            count = len(recipient_emails)
            self.message_user(
                request,
                ngettext(
                    "Email sent to %d user.",
                    "Email sent to %d users.",
                    count,
                )
                % count,
                messages.SUCCESS,
            )
            return redirect(reverse("admin:accounts_customuser_changelist"))

        context = {
            **self.admin_site.each_context(request),
            "title": _("Send email"),
            "form": form,
            "users": users,
        }
        return TemplateResponse(request, "admin/accounts/send_email.html", context)


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    model = Profile
    form = ProfileUpdateForm


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("recipient", "message", "is_read", "created_at", "created_by")
    list_filter = ("is_read",)
