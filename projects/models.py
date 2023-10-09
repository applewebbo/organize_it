from django.conf import settings
from django.db import models
from django_quill.fields import QuillField


class Project(models.Model):
    class Status(models.IntegerChoices):
        NOT_STARTED = 1
        IMPENDING = 2
        IN_PROGRESS = 3
        COMPLETED = 4

    title = models.CharField(max_length=100)
    description = QuillField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    due_date = models.CharField(max_length=100, null=True, blank=True)
    status = models.IntegerField(choices=Status.choices, default=Status.NOT_STARTED)

    def __str__(self) -> str:
        return self.title


class Link(models.Model):
    title = models.CharField(max_length=100, null=True, blank=True)
    url = models.URLField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.url
