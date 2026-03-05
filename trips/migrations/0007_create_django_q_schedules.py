from django.db import migrations


def create_schedules(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias

    schedules = [
        {
            "name": "Check Trips Status",
            "func": "trips.tasks.check_trips_status",
            "schedule_type": "C",
            "cron": "0 3 * * *",
            "repeats": -1,
        },
        {
            "name": "Cleanup Old Sessions",
            "func": "trips.tasks.cleanup_old_sessions",
            "schedule_type": "W",
            "repeats": -1,
        },
        {
            "name": "Database Backup",
            "func": "trips.tasks.backup_database",
            "schedule_type": "C",
            "cron": "0 2 * * 0",
            "repeats": -1,
        },
    ]

    for schedule in schedules:
        Schedule.objects.using(db_alias).get_or_create(
            func=schedule["func"],
            defaults=schedule,
        )


def delete_schedules(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    funcs = [
        "trips.tasks.check_trips_status",
        "trips.tasks.cleanup_old_sessions",
        "trips.tasks.backup_database",
    ]
    Schedule.objects.using(db_alias).filter(func__in=funcs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0006_maintransferconnection"),
        ("django_q", "0018_task_success_index"),
    ]

    operations = [
        migrations.RunPython(create_schedules, delete_schedules),
    ]
