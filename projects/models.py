import datetime

import geocoder
from django.conf import settings
from django.db import models


class Project(models.Model):
    class Status(models.IntegerChoices):
        NOT_STARTED = 1
        IMPENDING = 2
        IN_PROGRESS = 3
        COMPLETED = 4
        ARCHIVED = 5

    title = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.IntegerField(choices=Status.choices, default=Status.NOT_STARTED)
    links = models.ManyToManyField("Link", related_name="projects")

    class Meta:
        ordering = ("status",)

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        today = datetime.date.today()
        delta = today - datetime.timedelta(days=7)
        # more than 7 days from start date
        if self.start_date <= delta:
            self.status = 1
        # less than 7 days from start date
        elif self.start_date > delta and self.start_date < today:
            self.status = 2
        # between start date and end date
        elif self.start_date >= today and self.end_date >= today:
            self.status = 3
        # after end date
        elif self.end_date > today:
            self.status = 4
        else:
            self.status = 1

        super().save(*args, **kwargs)


class Link(models.Model):
    title = models.CharField(max_length=100, null=True, blank=True)
    url = models.URLField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="links"
    )

    def __str__(self) -> str:
        return self.url


class Place(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="places"
    )
    name = models.CharField(max_length=100)
    url = models.URLField(null=True, blank=True)
    address = models.CharField(max_length=200)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def save(self, *args, **kwargs):
        g = geocoder.mapbox(self.address, access_token=settings.MAPBOX_ACCESS_TOKEN)
        self.latitude, self.longitude = g.latlng
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
