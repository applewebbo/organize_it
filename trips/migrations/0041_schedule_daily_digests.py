from django.db import migrations


def create_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    Schedule.objects.using(db_alias).get_or_create(
        func="trips.tasks.send_daily_digests",
        defaults={
            "name": "Send Daily Digests",
            "func": "trips.tasks.send_daily_digests",
            "schedule_type": "C",
            "cron": "0 7 * * *",
            "repeats": -1,
        },
    )


def delete_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    Schedule.objects.using(db_alias).filter(
        func="trips.tasks.send_daily_digests"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0040_trip_daily_digest_sent_on"),
    ]

    operations = [
        migrations.RunPython(create_schedule, delete_schedule),
    ]
