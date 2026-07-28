from django.db import migrations

HOOK = "trips.utils.notify.notify_task_failure"


def set_hook(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    Schedule.objects.using(db_alias).update(hook=HOOK)


def unset_hook(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    db_alias = schema_editor.connection.alias
    Schedule.objects.using(db_alias).filter(hook=HOOK).update(hook="")


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0047_alter_staybooking_provider"),
        ("django_q", "0018_task_success_index"),
    ]

    operations = [
        migrations.RunPython(set_hook, unset_hook),
    ]
