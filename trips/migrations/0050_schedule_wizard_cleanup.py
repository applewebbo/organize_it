from django.db import migrations


def create_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    Schedule.objects.using(db_alias).get_or_create(
        func="trips.tasks.cleanup_abandoned_wizard_trips",
        defaults={
            "name": "Cleanup Abandoned Wizard Trips",
            "func": "trips.tasks.cleanup_abandoned_wizard_trips",
            "schedule_type": "C",
            "cron": "0 * * * *",
            "repeats": -1,
        },
    )


def delete_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    Schedule.objects.using(db_alias).filter(
        func="trips.tasks.cleanup_abandoned_wizard_trips"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0049_trip_wizard_completed_trip_wizard_started_at_and_more"),
        ("django_q", "0018_task_success_index"),
    ]

    operations = [
        migrations.RunPython(create_schedule, delete_schedule),
    ]
