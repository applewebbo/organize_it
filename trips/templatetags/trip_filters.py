import re

from django import template

from trips.data.phone_prefixes import ITALIAN_PREFIXES

register = template.Library()


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
