---
# async
title: Move geocoding to async task
status: todo
type: task
priority: "2"
created_at: 2026-03-30T13:06:33Z
updated_at: 2026-03-30T15:08:30Z
---

# Move geocoding to async task

## Objective
Eliminate geocoding latency from synchronous operations.

## Required changes

### 1. Create new task `trips/tasks.py`
```python
def geocode_object(model_name, object_id):
    """
    Geocode an object in background.

    Args:
        model_name: 'event', 'stay', or 'maintransfer'
        object_id: Primary key of the object
    """
    from trips.models import Event, Stay, MainTransfer
    import geocoder
    from django.conf import settings

    logger = logging.getLogger("task")

    try:
        if model_name == "event":
            obj = Event.objects.get(pk=object_id)
            address = f"{obj.address}, {obj.city}" if obj.city else obj.address
        elif model_name == "stay":
            obj = Stay.objects.get(pk=object_id)
            address = f"{obj.address}, {obj.city}" if obj.city else obj.address
        elif model_name == "maintransfer":
            obj = MainTransfer.objects.get(pk=object_id)
            if obj.type in [MainTransfer.Type.CAR, MainTransfer.Type.OTHER]:
                address = obj.origin_address
            else:
                return  # Skip non-car/other transfers
        else:
            logger.error(f"Unknown model: {model_name}")
            return

        if not address:
            return

        # Geocode
        g = geocoder.mapbox(address, access_token=settings.MAPBOX_ACCESS_TOKEN)
        if g and g.latlng:
            obj.latitude, obj.longitude = g.latlng
            obj.save(update_fields=["latitude", "longitude"])
            logger.info(f"Geocoded {model_name} {object_id}: {g.latlng}")
        else:
            logger.warning(f"Geocoding failed for {model_name} {object_id}")

    except Exception as e:
        logger.error(f"Error geocoding {model_name} {object_id}: {e}", exc_info=True)
```

### 2. Modify `trips/models.py` - Event.save() (line ~448)
```python
def save(self, *args, **kwargs):
    # Ensure trip is set from day if not already set
    if self.day and not self.trip_id:
        self.trip = self.day.trip

    super().save(*args, **kwargs)

    # Queue geocoding if address changed or coords missing
    if self.address and (self.latitude is None or self.longitude is None):
        from django_q.tasks import async_task
        async_task('trips.tasks.geocode_object', 'event', self.id)
```

### 3. Modify `trips/models.py` - Stay.save() (line ~149)
```python
def save(self, *args, **kwargs):
    super().save(*args, **kwargs)

    # Queue geocoding if address changed or coords missing
    if self.address and (self.latitude is None or self.longitude is None):
        from django_q.tasks import async_task
        async_task('trips.tasks.geocode_object', 'stay', self.id)
```

### 4. Modify `trips/models.py` - MainTransfer.save() (line ~305)
```python
def save(self, *args, **kwargs):
    """Override save - geocoding now async"""
    # Geocoding for CAR/OTHER moved to async task
    super().save(*args, **kwargs)

    # Queue geocoding if car/other with address
    if self.type in [self.Type.CAR, self.Type.OTHER]:
        if self.origin_address and (self.origin_latitude is None or self.origin_longitude is None):
            from django_q.tasks import async_task
            async_task('trips.tasks.geocode_object', 'maintransfer', self.id)
```

### 5. Remove synchronous geocoding from MainTransfer.save()
Remove lines ~314-328 containing synchronous geocoding.

## Test
1. Create event with address → immediate save
2. Wait for Q2 task → verify coordinates updated
3. Check `tasks.log` for errors
4. Run `just ftest`

## Acceptance criteria
- [ ] Event/Stay/MainTransfer save < 50ms
- [ ] Geocoding completed in background within 5s
- [ ] All tests pass
- [ ] Tasks logged correctly

Codeberg issue: #256
