from django.contrib import admin

from .models import (
    Attachment,
    ChecklistItem,
    Day,
    Expense,
    ExpenseParticipant,
    ExpenseShare,
    Experience,
    FamilyUnit,
    Link,
    MainTransfer,
    MainTransferConnection,
    Meal,
    ShareLink,
    Stay,
    StayBooking,
    Trip,
    TripCollaboration,
    TripInvitation,
)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "status", "start_date", "end_date"]
    list_filter = ["status"]


admin.site.register(Link)


@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "trip",
        "date",
        "destination",
        "destination_latitude",
        "destination_longitude",
        "transfer_duration_from_prev",
        "transfer_distance_from_prev",
    ]
    search_fields = ["destination", "trip__title"]
    list_filter = ["trip"]


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ["name", "day", "category", "order"]
    list_filter = ["category", "day__trip"]


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ["name", "day", "category", "order"]
    list_filter = ["category", "day__trip"]


@admin.register(Stay)
class StayAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(FamilyUnit)
class FamilyUnitAdmin(admin.ModelAdmin):
    list_display = ["__str__", "trip"]
    list_filter = ["trip"]


@admin.register(ExpenseParticipant)
class ExpenseParticipantAdmin(admin.ModelAdmin):
    list_display = ["__str__", "trip", "family_unit", "is_child", "is_active"]
    list_filter = ["trip", "is_child", "is_active"]


class ExpenseShareInline(admin.TabularInline):
    model = ExpenseShare
    extra = 0


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["title", "trip", "amount", "date", "payer"]
    list_filter = ["trip"]
    inlines = [ExpenseShareInline]


@admin.register(MainTransfer)
class MainTransferAdmin(admin.ModelAdmin):
    list_display = ["trip", "direction", "type", "start_time"]
    list_filter = ["trip", "direction", "type"]


@admin.register(MainTransferConnection)
class MainTransferConnectionAdmin(admin.ModelAdmin):
    list_display = ["main_transfer", "event", "stay", "transport_mode"]


@admin.register(TripCollaboration)
class TripCollaborationAdmin(admin.ModelAdmin):
    list_display = ["trip", "user", "participant_name", "can_edit"]
    list_filter = ["trip"]


@admin.register(TripInvitation)
class TripInvitationAdmin(admin.ModelAdmin):
    list_display = ["trip", "email", "invited_by", "is_accepted", "expires_at"]


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ["trip", "permission_level", "is_active", "expires_at"]


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ["trip", "text", "completed"]
    list_filter = ["trip", "completed"]


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ["content_object", "original_name", "mime_type", "uploaded_by"]


@admin.register(StayBooking)
class StayBookingAdmin(admin.ModelAdmin):
    list_display = ["trip", "destination", "provider", "hotel_name", "created_by"]
