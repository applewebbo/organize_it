from datetime import date, timedelta

import geocoder
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext as _


def days_between(start_date, end_date):
    delta = end_date - start_date
    return delta.days


class Trip(models.Model):
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
    status = models.IntegerField(choices=Status, default=Status.NOT_STARTED)
    links = models.ManyToManyField("Link", related_name="trips", blank=True)

    class Meta:
        ordering = ("status",)

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            # add the case for when status is 5 to bypass date checks
            if self.status == 5:
                super().save(*args, **kwargs)
                return
            today = date.today()
            seven_days_after = today + timedelta(days=7)
            # after end date
            if self.end_date < today:
                self.status = 4
            # between start date and end date
            elif self.start_date <= today and self.end_date >= today:
                self.status = 3
            # less than 7 days from start date
            elif self.start_date < seven_days_after and self.start_date > today:
                self.status = 2
            # more than 7 days from start date
            elif self.start_date <= seven_days_after:
                self.status = 1

        super().save(*args, **kwargs)


@receiver(post_save, sender=Trip)
def update_trip_days(sender, instance, **kwargs):
    if not instance.start_date or not instance.end_date:
        return
    days = days_between(instance.start_date, instance.end_date)
    # check if days already created are inside the range and delete them accordingly
    for day in instance.days.all():
        if day.date < instance.start_date or day.date > instance.end_date:
            day.delete()
    for day in range(days + 1):
        Day.objects.update_or_create(
            trip=instance,
            number=day + 1,
            date=instance.start_date + timedelta(days=day),
        )


class Day(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="days")
    number = models.PositiveSmallIntegerField()
    date = models.DateField()

    def __str__(self) -> str:
        day = _("Day")
        return f"{day} {self.number}"


class Link(models.Model):
    title = models.CharField(max_length=100, null=True, blank=True)
    url = models.URLField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="links"
    )

    def __str__(self) -> str:
        return self.url


class NotAssignedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(day__isnull=True)


class Place(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="places")
    day = models.ForeignKey(
        Day, on_delete=models.SET_NULL, null=True, related_name="places"
    )
    name = models.CharField(max_length=100)
    url = models.URLField(null=True, blank=True)
    address = models.CharField(max_length=200)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    objects = models.Manager()
    na_objects = NotAssignedManager()

    def save(self, *args, **kwargs):
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        # if address is not changed, don't update coordinates
        if old and old.address == self.address:
            return super().save(*args, **kwargs)
        g = geocoder.mapbox(self.address, access_token=settings.MAPBOX_ACCESS_TOKEN)
        self.latitude, self.longitude = g.latlng
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Note(models.Model):
    content = models.CharField(max_length=500)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="notes")
    place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True, blank=True)
    link = models.ForeignKey(Link, on_delete=models.SET_NULL, null=True, blank=True)
    checked = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.content[:35]} ..."
