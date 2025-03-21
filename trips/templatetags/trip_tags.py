import re

from django import template

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
    days = list(day.trip.days.all())
    try:
        current_index = days.index(day)
        return current_index == len(days) - 1
    except (ValueError, IndexError):
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
    return day.number == 1


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
        1: "bg-[#BAEAFF]",  # Transport
        2: "bg-[#DDFFCF]",  # Experience
        3: "bg-[#FFF4D4]",  # Meal
    }
    return colors.get(event.category, "bg-gray-300")


@register.filter
def event_border_color(event):
    colors = {
        1: "border-[#5ECEFF]",  # Transport
        2: "border-[#98F56F]",  # Experience
        3: "border-[#FFDB6D]",  # Meal
    }
    return colors.get(event.category, "bg-gray-300")


@register.filter
def event_icon_color(event):
    colors = {
        1: "text-transport-blue",  # Transport
        2: "text-experience-green",  # Experience
        3: "text-meal-yellow",  # Meal
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
