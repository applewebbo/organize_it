import django.db.models.deletion
from django.db import migrations, models


def set_trip_from_day(apps, schema_editor):
    """Set trip field for existing events based on their day relationship"""
    Event = apps.get_model("trips", "Event")
    Trip = apps.get_model("trips", "Trip")

    # Get a default trip for events without a day
    default_trip = Trip.objects.first()
    if not default_trip:
        default_trip = Trip.objects.create(title="Default Trip")

    for event in Event.objects.select_related("day__trip").all():
        event.trip = event.day.trip if event.day else default_trip
        event.save()


def reverse_trip_from_day(apps, schema_editor):
    """Reverse migration - no action needed as trip data is derived from day"""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0016_alter_event_day"),
    ]

    operations = [
        # 1. Add trip field as nullable first
        migrations.AddField(
            model_name="event",
            name="trip",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="all_events",
                to="trips.trip",
            ),
        ),
        # 2. Update day field to allow null
        migrations.AlterField(
            model_name="event",
            name="day",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="events",
                to="trips.day",
            ),
        ),
        # 3. Set trip values for all events
        migrations.RunPython(set_trip_from_day, reverse_trip_from_day),
        # 4. Make trip field non-nullable after data migration
        migrations.AlterField(
            model_name="event",
            name="trip",
            field=models.ForeignKey(
                null=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="all_events",
                to="trips.trip",
            ),
        ),
    ]
