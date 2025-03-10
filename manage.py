#!/usr/bin/env python
import os
import sys
import warnings


def main():
    # Filter out specific deprecation warnings from Typer
    warnings.filterwarnings(
        "ignore", message="In Typer, only the parameter.*", category=DeprecationWarning
    )

    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.common")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
