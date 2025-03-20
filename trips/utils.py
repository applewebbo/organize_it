from django.db.models import BooleanField, Case, F, Q, When, Window
from django.db.models.functions import Lag, Lead


def annotate_event_overlaps(queryset):
    """
    Annotates events with overlap information using window functions.
    An event overlaps when either:
    - Its start time is before the next event's end time
    - Its end time is after the previous event's start time

    Returns: Queryset annotated with has_overlap boolean field
    """
    return queryset.annotate(
        next_start=Window(
            expression=Lead("start_time"), partition_by="day_id", order_by="start_time"
        ),
        prev_end=Window(
            expression=Lag("end_time"), partition_by="day_id", order_by="start_time"
        ),
    ).annotate(
        has_overlap=Case(
            When(
                Q(end_time__gt=F("next_start")) | Q(start_time__lt=F("prev_end")),
                then=True,
            ),
            default=False,
            output_field=BooleanField(),
        )
    )
