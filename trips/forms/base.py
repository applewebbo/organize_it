"""Shared form helpers and crispy layout snippets used across the forms package."""

from django.db import models


def urlfields_assume_https(db_field, **kwargs):
    """
    ModelForm.Meta.formfield_callback function to assume HTTPS for scheme-less
    domains in URLFields.
    """
    if isinstance(db_field, models.URLField):
        kwargs["assume_scheme"] = "https"
    return db_field.formfield(**kwargs)


ADDRESS_RESULTS_HTML = """
    <div id="address-results" class="sm:col-span-4">
    <!-- Address Results will be added here.. -->
    </div>
"""

TAG_RESULTS_HTML = """
    <div id="tag-results" class="sm:col-start-3 sm:col-span-2 -mt-3">
    </div>
"""
