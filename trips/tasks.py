from django.conf import settings
from django.core import management  # pragma: no cover


def populate_trips():  # pragma: no cover
    if settings.DEBUG:
        management.call_command("populate_trips", "--settings=trips.settings.dev")
    else:
        management.call_command(
            "populate_trips", "--settings=trips.settings.production"
        )
    print("Trips populated correctly!")
