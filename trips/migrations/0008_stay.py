# Generated by Django 5.1.6 on 2025-02-24 09:56

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0007_meal"),
    ]

    operations = [
        migrations.CreateModel(
            name="Stay",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("check_in", models.TimeField(blank=True, null=True)),
                ("check_out", models.TimeField(blank=True, null=True)),
                ("cancellation_date", models.DateField(blank=True, null=True)),
                (
                    "phone_number",
                    models.CharField(
                        blank=True,
                        max_length=30,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Enter a valid phone number (with or without international prefix).",
                                regex="^(?:\\+?[1-9]\\d{1,14}|\\d{2,15})$",
                            )
                        ],
                    ),
                ),
                ("url", models.URLField(blank=True, null=True)),
                ("address", models.CharField(max_length=200)),
                ("latitude", models.FloatField(blank=True, null=True)),
                ("longitude", models.FloatField(blank=True, null=True)),
                ("days", models.ManyToManyField(related_name="stays", to="trips.day")),
            ],
        ),
    ]
