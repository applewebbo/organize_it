from django.db import migrations


def create_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    Schedule.objects.using(db_alias).get_or_create(
        func="trips.tasks.fetch_weather_for_active_trips",
        defaults={
            "name": "Fetch Weather for Active Trips",
            "func": "trips.tasks.fetch_weather_for_active_trips",
            "schedule_type": "C",
            "cron": "0 */6 * * *",
            "repeats": -1,
        },
    )


def delete_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    Schedule.objects.using(db_alias).filter(
        func="trips.tasks.fetch_weather_for_active_trips"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0009_day_weather_data_day_weather_fetched_at"),
        ("django_q", "0018_task_success_index"),
    ]

    operations = [
        migrations.RunPython(create_schedule, delete_schedule),
    ]
