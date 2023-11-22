# Generated by Django 4.2.7 on 2023-11-22 14:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0008_alter_project_links"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="links",
            field=models.ManyToManyField(
                blank=True, related_name="projects", to="projects.link"
            ),
        ),
    ]
