---
# cache
title: Cache Profile lookup
status: todo
type: task
priority: "1"
created_at: 2026-03-30T13:06:33Z
updated_at: 2026-03-30T15:08:30Z
---

# Cache Profile lookup

## Objective
Reduce Profile queries from N (one per request) to 1 every 5 minutes.

## Required changes

### 1. `trips/utils.py` - get_trips() (line ~52)
```python
from django.core.cache import cache

def get_trips(user):
    # Cache Profile for 5 minutes
    profile = cache.get_or_set(
        f"profile_{user.id}",
        lambda: Profile.objects.select_related("fav_trip").get(user=user),
        timeout=300  # 5 minutes
    )
    fav_trip = profile.fav_trip
    # ... rest of code
```

### 2. `trips/views.py` - home() (line ~76)
```python
def home(request):
    """Home page"""
    context = {}
    if request.user.is_authenticated:
        # Use cache instead of direct query
        profile = cache.get_or_set(
            f"profile_{request.user.id}",
            lambda: Profile.objects.select_related("fav_trip").get(user=request.user),
            timeout=300
        )
        context = get_trips(request.user)
        context["show_guide"] = request.session.get("show_guide", False)
    return TemplateResponse(request, "trips/index.html", context)
```

### 3. `trips/views.py` - trip_detail() (line ~158)
```python
# Replace:
default_view = request.user.profile.default_map_view

# With:
profile = cache.get_or_set(
    f"profile_{request.user.id}",
    lambda: Profile.objects.select_related("fav_trip").get(user=request.user),
    timeout=300
)
default_view = profile.default_map_view
```

## Test
1. Run `just ftest`
2. Verify cache hit rate with Django Debug Toolbar
3. Test cache invalidation after logout/login

## Acceptance criteria
- [ ] Profile query reduced to 1 every 5 minutes per user
- [ ] All tests pass
- [ ] Cache invalidated correctly on logout

Codeberg issue: #255
