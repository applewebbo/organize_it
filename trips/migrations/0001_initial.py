# Generated by Django 5.1.7 on 2025-04-03 06:02

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Day",
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
                ("number", models.PositiveSmallIntegerField()),
                ("date", models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name="Event",
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
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("url", models.URLField(blank=True, null=True)),
                ("address", models.CharField(max_length=200)),
                ("latitude", models.FloatField(blank=True, null=True)),
                ("longitude", models.FloatField(blank=True, null=True)),
                (
                    "category",
                    models.PositiveSmallIntegerField(
                        choices=[(1, "Transport"), (2, "Experience"), (3, "Meal")],
                        default=2,
                    ),
                ),
                (
                    "day",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="events",
                        to="trips.day",
                    ),
                ),
            ],
            options={
                "ordering": ["start_time"],
            },
        ),
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
            ],
        ),
        migrations.CreateModel(
            name="Experience",
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
                            (1, "Museum"),
                            (2, "Park"),
                            (3, "Walk"),
                            (4, "Sport"),
                            (6, "Other"),
                        ],
                        default=1,
                    ),
                ),
            ],
            bases=("trips.event",),
        ),
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
        migrations.CreateModel(
            name="Transport",
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
                            (1, "Car"),
                            (2, "Plane"),
                            (3, "Train"),
                            (4, "Boat"),
                            (5, "Bus"),
                            (6, "Taxi"),
                            (7, "Other"),
                        ],
                        default=1,
                    ),
                ),
                ("destination", models.CharField(max_length=100)),
                ("dest_latitude", models.FloatField(blank=True, null=True)),
                ("dest_longitude", models.FloatField(blank=True, null=True)),
            ],
            bases=("trips.event",),
        ),
        migrations.CreateModel(
            name="Link",
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
                ("title", models.CharField(blank=True, max_length=100, null=True)),
                ("url", models.URLField()),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="links",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="day",
            name="stay",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="days",
                to="trips.stay",
            ),
        ),
        migrations.CreateModel(
            name="Trip",
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
                ("title", models.CharField(max_length=100)),
                ("description", models.CharField(max_length=500)),
                ("destination", models.CharField(max_length=100)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.IntegerField(
                        choices=[
                            (1, "Not Started"),
                            (2, "Impending"),
                            (3, "In Progress"),
                            (4, "Completed"),
                            (5, "Archived"),
                        ],
                        default=1,
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "links",
                    models.ManyToManyField(
                        blank=True, related_name="trips", to="trips.link"
                    ),
                ),
            ],
            options={
                "ordering": ("status",),
            },
        ),
        migrations.CreateModel(
            name="Note",
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
                ("content", models.CharField(max_length=500)),
                ("checked", models.BooleanField(default=False)),
                (
                    "link",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="trips.link",
                    ),
                ),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notes",
                        to="trips.trip",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="event",
            name="trip",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="all_events",
                to="trips.trip",
            ),
        ),
        migrations.AddField(
            model_name="day",
            name="trip",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="days",
                to="trips.trip",
            ),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(
                fields=["day_id", "start_time"], name="trips_event_day_id_7669b5_idx"
            ),
        ),
    ]
