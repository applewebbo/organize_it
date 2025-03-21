# Generated by Django 5.1.6 on 2025-02-23 15:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0006_experience"),
    ]

    operations = [
        migrations.CreateModel(
            name="Meal",
            fields=[
                (
                    "event_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="trips.event",
                    ),
                ),
                (
                    "type",
                    models.IntegerField(
                        choices=[
                            (1, "Breakfast"),
                            (2, "Lunch"),
                            (3, "Dinner"),
                            (4, "Snack"),
                        ],
                        default=2,
                    ),
                ),
            ],
            bases=("trips.event",),
        ),
    ]
