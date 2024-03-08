from django.core import management


def populate_trips():
    management.call_command("populate_trips", "--settings=trips.settings.dev")
    print("Trips populated correctly!")
