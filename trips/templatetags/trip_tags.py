import re

from django import template
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import format_html, format_html_join

from trips.data.phone_prefixes import ITALIAN_PREFIXES

register = template.Library()


@register.filter
def format_opening_hours(hours_data):
    """
    Formats opening hours from Google Places API by grouping consecutive days with the same hours,
    with the week starting on Monday.
    """
    if not isinstance(hours_data, dict):
        return ""

    if "periods" not in hours_data:
        descriptions = hours_data.get("weekdayDescriptions", [])
        if not descriptions:
            return ""
        list_items = format_html_join("", "<li>{}</li>", ((d,) for d in descriptions))
        return format_html('<ul class="list-none p-0 m-0">{}</ul>', list_items)

    day_names = {0: "Dom", 1: "Lun", 2: "Mar", 3: "Mer", 4: "Gio", 5: "Ven", 6: "Sab"}
    hours_by_day = {i: "Chiuso" for i in range(7)}

    for period in hours_data.get("periods", []):
        if "open" in period and "close" in period:
            day = period["open"]["day"]
            open_time = f"{period['open']['hour']:02d}:{period['open']['minute']:02d}"
            close_time = (
                f"{period['close']['hour']:02d}:{period['close']['minute']:02d}"
            )
            hours_by_day[day] = f"{open_time} – {close_time}"

    output_lines = []
    week_order = [1, 2, 3, 4, 5, 6, 0]  # Monday to Sunday

    i = 0
    while i < 7:
        start_of_week_index = i
        google_day_index = week_order[start_of_week_index]
        current_hours = hours_by_day[google_day_index]

        j = i
        while j + 1 < 7 and hours_by_day[week_order[j + 1]] == current_hours:
            j += 1
        end_of_week_index = j

        start_day_name = day_names[week_order[start_of_week_index]]
        end_day_name = day_names[week_order[end_of_week_index]]

        if start_of_week_index == end_of_week_index:
            day_range_str = start_day_name
        else:
            day_range_str = f"{start_day_name}-{end_day_name}"

        output_lines.append(
            format_html("<strong>{}:</strong> {}", day_range_str, current_hours)
        )
        i = j + 1

    if not output_lines:
        return ""

    list_items = format_html_join("", "<li>{}</li>", ((line,) for line in output_lines))
    return format_html(
        '<ul class="list-none p-0 m-0 leading-normal">{}</ul>', list_items
    )


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
        1: "car-profile",  # Transport
        2: "images",  # Experience
        3: "fork-knife",  # Meal
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
