# Test Suite Documentation

This document describes the organization, patterns, and best practices for the Organize It test suite.

## Overview

The test suite uses **pytest** with **factory-boy** for model factories and **django-test-plus** for enhanced Django test utilities. All tests target **100% code coverage** and follow consistent patterns for maintainability.

**Key Statistics:**
- Total tests: 568
- Coverage: 100%
- Test framework: pytest + pytest-django
- Parallel execution: 8 workers (via pytest-xdist)

## Project Structure

```
tests/
├── README.md                    # This file
├── test.py                      # Base TestCase class
├── helpers.py                   # Shared helper functions
│
├── accounts/                    # Account app tests
│   ├── factories.py            # User/Profile factories
│   ├── test_models.py          # User/Profile model tests
│   ├── test_forms.py           # Form tests
│   └── test_views.py           # View tests
│
└── trips/                       # Trips app tests
    ├── conftest.py             # Pytest fixtures (trips-specific)
    ├── factories.py            # Trip/Day/Event/Stay factories
    │
    ├── test_models.py          # Model tests
    ├── test_forms.py           # Form tests
    ├── test_signals.py         # Signal tests
    ├── test_template_tags.py   # Template tag tests
    │
    ├── test_views.py           # Core navigation views
    ├── test_views_trip_crud.py           # Trip CRUD operations
    ├── test_views_event_crud.py          # Event creation/modification
    ├── test_views_stay_crud.py           # Stay CRUD operations
    ├── test_views_event_operations.py    # Event advanced operations
    ├── test_views_notes.py               # Notes management
    ├── test_views_enrichment.py          # Google Places integration
    ├── test_views_main_transfer.py       # Main transfer views
    ├── test_image_views.py               # Image handling views
    │
    ├── test_utils.py           # Utility function tests
    ├── test_utils_csv.py       # CSV export utilities
    ├── test_utils_geocoding.py # Geocoding utilities
    │
    ├── test_commands.py        # Management command tests
    ├── test_tasks.py           # Django-Q2 background task tests
    └── test_trip_image_integration.py    # Unsplash integration
```

## Testing Patterns

The test suite uses a **hybrid approach** combining unittest-style test classes with pytest features:

### Unittest-Style Tests (Preferred for Views)

Most view tests use the **django-test-plus** `TestCase` class:

```python
import pytest
from tests.test import TestCase
from tests.trips.factories import TripFactory

pytestmark = pytest.mark.django_db


class TripDetailView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        self.response_200(response)
        assert response.context["trip"] == trip
```

**Advantages:**
- Familiar Django-style test structure
- Built-in helper methods (`self.get()`, `self.post()`, `self.response_200()`)
- Automatic user creation (`self.make_user()`)
- Context manager for login (`with self.login(user):`)

### Pytest-Style Tests

Some tests use pure pytest functions with fixtures:

```python
import pytest
from trips.models import Trip


def test_trip_creation(trip_factory):
    """Test trip model creation."""
    trip = trip_factory(title="Paris Trip")
    assert trip.title == "Paris Trip"
    assert Trip.objects.count() == 1
```

**When to use:**
- Model tests
- Utility function tests
- Tests requiring parametrization
- Tests with complex fixture dependencies

## Base TestCase Class

All view tests inherit from `tests.test.TestCase`, which extends `django-test-plus.TestCase`:

```python
from tests.test import TestCase


class MyViewTest(TestCase):
    """
    Available methods:
    - self.make_user(username) - Create and return user
    - self.get(url_name, **kwargs) - GET request
    - self.post(url_name, data=..., **kwargs) - POST request
    - self.delete(url_name, **kwargs) - DELETE request
    - self.login(user) - Context manager for authenticated requests
    - self.response_200(response) - Assert 200 status
    - self.response_204(response) - Assert 204 status
    - self.response_302(response) - Assert redirect
    - self.response_404(response) - Assert not found
    """
    pass
```

**Important:** Always add `pytestmark = pytest.mark.django_db` at the module level to enable database access.

## Shared Fixtures

### Trips-Specific Fixtures (`tests/trips/conftest.py`)

```python
import pytest


@pytest.fixture
def authenticated_user(client, user_factory):
    """Create and login a user, return (user, client) tuple."""
    user = user_factory()
    client.force_login(user)
    return user, client


@pytest.fixture
def trip_with_days(user_factory, trip_factory):
    """Create a trip with user and pre-generated days."""
    user = user_factory()
    trip = trip_factory(author=user)
    return trip, user


@pytest.fixture
def trip_day_event(user_factory, trip_factory, event_factory):
    """Create complete trip->day->event hierarchy."""
    user = user_factory()
    trip = trip_factory(author=user)
    day = trip.days.first()
    event = event_factory(day=day)
    return trip, day, event, user
```

**Usage:**

```python
def test_with_trip(trip_with_days):
    trip, user = trip_with_days
    assert trip.author == user
    assert trip.days.count() > 0


def test_with_hierarchy(trip_day_event):
    trip, day, event, user = trip_day_event
    assert event.day == day
    assert day.trip == trip
```

### Factory Fixtures (Auto-registered by pytest-factoryboy)

All factories in `tests/*/factories.py` are automatically available as fixtures:

```python
# Available fixtures (snake_case of factory names):
# - user_factory
# - profile_factory
# - trip_factory
# - day_factory
# - event_factory
# - transport_factory
# - experience_factory
# - meal_factory
# - stay_factory
# etc.

def test_with_factories(user_factory, trip_factory):
    user = user_factory(email="test@example.com")
    trip = trip_factory(author=user, title="Test Trip")
    assert trip.author == user
```

## Helper Functions

The `tests/helpers.py` module provides reusable helper functions:

### Message Assertions

```python
from tests.helpers import (
    assert_success_message,
    assert_no_messages,
    get_first_message,
)


def test_create_trip(self):
    # ... create trip ...

    # Assert specific message
    assert_success_message(response, "Trip created successfully")

    # Or get message for custom assertion
    message = get_first_message(response)
    assert "created" in message.lower()

    # Assert no messages
    assert_no_messages(response)
```

### Data Builders

Helpers for building common form data:

```python
from tests.helpers import (
    build_trip_data,
    build_transport_data,
    build_experience_data,
    build_meal_data,
    build_stay_data,
)


def test_trip_creation():
    # Build trip data with defaults
    data = build_trip_data()
    # {'title': 'Test Trip', 'destination': 'Test City', ...}

    # Override specific fields
    data = build_trip_data(
        title="Paris Trip",
        destination="Paris",
        start_date=date(2024, 6, 1),
    )
```

**Available builders:**
- `build_trip_data(**kwargs)` - Trip form data
- `build_experience_data(**kwargs)` - Experience event data
- `build_meal_data(**kwargs)` - Meal event data
- `build_stay_data(**kwargs)` - Stay form data

## Running Tests

### Basic Commands

```bash
# Run all tests (parallel, fast)
just ftest

# Run all tests (serial, verbose)
just test

# Run specific file
just ftest tests/trips/test_views.py

# Run specific test class
just ftest tests/trips/test_views.py::TripDetailView

# Run specific test method
just ftest tests/trips/test_views.py::TripDetailView::test_get

# Run tests excluding mapbox tests
just mptest
```

### Coverage Reports

```bash
# HTML coverage report (open htmlcov/index.html)
just ftest

# Terminal coverage report
pytest --cov=. --cov-report=term-missing
```

### Debugging Tests

```bash
# Run with print statements visible
pytest tests/trips/test_views.py -s

# Run with detailed output
pytest tests/trips/test_views.py -vv

# Run and stop at first failure
pytest tests/trips/test_views.py -x

# Run last failed tests only
pytest --lf
```

## Best Practices

### 1. Use Factories, Not Fixtures for Models

✅ **Good:**
```python
def test_trip_status(trip_factory):
    trip = trip_factory(start_date=date.today())
    assert trip.status == Trip.Status.IMPENDING
```

❌ **Avoid:**
```python
@pytest.fixture
def trip():
    return Trip.objects.create(...)  # Too rigid
```

### 2. Mock External Services

Always mock external API calls (Mapbox, Google Places, Unsplash):

```python
@patch("geocoder.mapbox")
def test_geocoding(mock_geocoder):
    mock_geocoder.return_value.latlng = [45.4773, 9.1815]
    # ... test code ...
```

### 3. Test Both Success and Failure Paths

```python
class TripCreateView(TestCase):
    def test_post_success(self):
        # Test successful creation
        pass

    def test_post_invalid_dates(self):
        # Test validation error
        pass

    def test_post_unauthenticated(self):
        # Test permission denied
        pass
```

### 4. Use Descriptive Test Names

```python
# Good: Describes what is being tested
def test_trip_status_changes_to_in_progress_when_start_date_is_today(self):
    pass

# Avoid: Vague names
def test_status(self):
    pass
```

### 5. Organize Tests by Feature, Not by Model

The `test_views.py` split demonstrates this:
- `test_views_trip_crud.py` - Trip operations
- `test_views_event_crud.py` - Event operations
- `test_views_notes.py` - Notes feature
- `test_views_enrichment.py` - Google Places feature

### 6. Keep Tests Independent

Each test should be able to run in isolation:

```python
# Good: Creates own data
def test_trip_list(self):
    user = self.make_user("user")
    trip1 = TripFactory(author=user)
    trip2 = TripFactory(author=user)
    # ... test ...

# Avoid: Depends on other tests
class TripTests(TestCase):
    def setUp(self):
        self.trip = TripFactory()  # Shared state
```

### 7. Use Time Machine for Date Tests

```python
import time_machine


@time_machine.travel("2024-06-01 12:00:00")
def test_trip_status_at_specific_date(self):
    trip = TripFactory(start_date=date(2024, 6, 1))
    assert trip.status == Trip.Status.IN_PROGRESS
```

## Common Patterns

### Testing Views with Authentication

```python
class TripUpdateView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-update", pk=trip.pk)

        self.response_200(response)
```

### Testing HTMX Views

```python
def test_htmx_response(self):
    response = self.get("trips:trip-modal", pk=trip.pk, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert "HX-Trigger" in response.headers
```

### Testing Messages

```python
from django.contrib.messages import get_messages


def test_success_message(self):
    response = self.post("trips:trip-create", data=data)
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].message == "Trip created successfully"
```

### Testing Form Validation

```python
def test_form_invalid_dates(self):
    data = build_trip_data(
        start_date=date.today() + timedelta(days=3),
        end_date=date.today(),
    )

    response = self.post("trips:trip-create", data=data)
    self.response_200(response)  # Re-renders form
    assert "Start date must be before end date" in response.content.decode()
```

## Troubleshooting

### "No module named 'tests'"

Make sure you're running tests from the project root and `PYTHONPATH` includes the project root.

### "Database access not allowed"

Add `pytestmark = pytest.mark.django_db` at the top of your test module.

### "Factory not found"

Ensure the factory is:
1. Defined in a `factories.py` file
2. Named with "Factory" suffix (e.g., `TripFactory`)
3. The test file imports pytest-factoryboy

### Tests are slow

Use `just ftest` for parallel execution with 8 workers instead of `just test`.

## Maintaining Tests

### Adding New Tests

1. **Choose appropriate file** based on feature (CRUD, operations, etc.)
2. **Use existing patterns** from similar tests
3. **Add factories** if testing new models
4. **Verify coverage** remains at 100%

### Refactoring Tests

1. **Keep tests passing** at each step
2. **Run full suite** after changes (`just ftest`)
3. **Update this documentation** if patterns change
4. **Commit frequently** with descriptive messages

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [factory-boy](https://factoryboy.readthedocs.io/)
- [django-test-plus](https://django-test-plus.readthedocs.io/)
- [pytest-xdist (parallel execution)](https://pytest-xdist.readthedocs.io/)
