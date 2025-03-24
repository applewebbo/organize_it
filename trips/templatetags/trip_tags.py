import re

from django import template
from django.core.exceptions import ObjectDoesNotExist

from trips.data.phone_prefixes import ITALIAN_PREFIXES

register = template.Library()


@register.filter
def next_day(day):
    days = list(day.trip.days.all())
    try:
        current_index = days.index(day)
        return days[current_index + 1] if current_index + 1 < len(days) else None
    except (ValueError, IndexError):
        return None


@register.filter
def is_last_day(day):
    try:
        days = list(day.trip.days.all())
        current_index = days.index(day)
        return current_index == len(days) - 1
    except (ValueError, IndexError, ObjectDoesNotExist):
        return False


@register.filter
def has_different_stay(day1, day2):
    if not day2:
        return True
    return day1.stay != day2.stay


@register.filter
def is_first_day_of_stay(day):
    if not day.stay:
        return False
    prev_day = day.prev_day
    return not prev_day or prev_day.stay != day.stay


@register.filter
def is_first_day_of_trip(day):
    """Check if the given day is the first day of its trip using prefetched data"""
    try:
        days = [d for d in day.trip.days.all()]
        first_day = min(days, key=lambda d: d.number) if days else None
        return day == first_day
    except AttributeError:
        return False


@register.filter
def event_icon(event):
    icons = {
        1: "truck",  # Transport
        2: "photo",  # Experience
        3: "cake",  # Meal
    }
    return icons.get(event.category, "question-mark-circle")


@register.filter
def event_bg_color(event):
    colors = {
        1: "bg-tr-blue-100 dark:bg-tr-blue-100/30",  # Transport
        2: "bg-exp-green-100 dark:bg-exp-green-100/30",  # Experience
        3: "bg-meal-yellow-100 dark:bg-meal-yellow-100/30",  # Meal
    }
    return colors.get(event.category, "bg-gray-100")


@register.filter
def event_border_color(event):
    colors = {
        1: "border-tr-blue-300 dark:border-tr-blue-700",  # Transport
        2: "border-exp-green-300 dark:border-exp-green-700",  # Experience
        3: "border-meal-yellow-300 dark:border-meal-yellow-700",  # Meal
    }
    return colors.get(event.category, "border-gray-300")


@register.filter
def event_icon_color(event):
    colors = {
        1: "text-tr-blue-700 dark:text-tr-blue-300",  # Transport
        2: "text-exp-green-700 dark:text-exp-green-300",  # Experience
        3: "text-meal-yellow-700 dark:text-meal-yellow-300",  # Meal
    }
    return colors.get(event.category, "text-base-content")


@register.filter
def phone_format(value):
    """Format phone number to European style (+## ###########)"""
    if not value:
        return value

    # Remove any non-digit characters except plus
    number = re.sub(r"[^\d+]", "", str(value))

    # If number doesn't start with +, assume it's a local number and add +39 (Italy)
    if not number.startswith("+"):
        number = "+39" + number

    # Split into country code and rest
    country_code = number[:3]  # Including the +
    rest = number[3:]

    # Format rest based on type of number
    if rest.startswith("3"):  # Mobile number
        formatted_rest = f"{rest[:3]} {rest[3:]}"
    else:  # Check for landline prefixes
        for prefix in ITALIAN_PREFIXES:
            if rest.startswith(prefix):
                formatted_rest = f"{rest[: len(prefix)]} {rest[len(prefix) :]}"
                break
        else:  # If no prefix matches, don't split
            formatted_rest = rest

    return f"{country_code} {formatted_rest}"
