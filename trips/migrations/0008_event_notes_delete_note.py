# Generated by Django 5.2.1 on 2025-05-17 08:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0007_stay_notes"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="notes",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.DeleteModel(
            name="Note",
        ),
    ]
