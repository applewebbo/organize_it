# Generated by Django 5.1.6 on 2025-02-24 13:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0008_stay"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="stay",
            name="days",
        ),
        migrations.AddField(
            model_name="day",
            name="stay",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="days",
                to="trips.stay",
            ),
        ),
    ]
