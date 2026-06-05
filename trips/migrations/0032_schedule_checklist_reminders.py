from django.db import migrations


def create_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    Schedule.objects.using(db_alias).get_or_create(
        func="trips.tasks.send_checklist_reminders",
        defaults={
            "name": "Send Checklist Reminders",
            "func": "trips.tasks.send_checklist_reminders",
            "schedule_type": "C",
            "cron": "0 8 * * *",
            "repeats": -1,
        },
    )


def delete_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    Schedule.objects.using(db_alias).filter(
        func="trips.tasks.send_checklist_reminders"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0031_trip_checklist_reminder_days_and_more"),
        ("django_q", "0018_task_success_index"),
    ]

    operations = [
        migrations.RunPython(create_schedule, delete_schedule),
    ]
