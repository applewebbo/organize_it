# Generated by Django 5.1.7 on 2025-03-12 13:41

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0013_remove_note_place_alter_day_stay_delete_place"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="category",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "Transport"), (2, "Experience"), (3, "Meal")], default=2
            ),
        ),
    ]
