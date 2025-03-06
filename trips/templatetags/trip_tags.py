from django import template

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
