"""Test helper functions and utilities"""

from datetime import date, timedelta

from django.contrib.messages import get_messages


def assert_success_message(response, expected_message):
    """Assert that response contains expected success message."""
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) > 0, "No messages found in response"
    assert messages[0].message == expected_message


def assert_no_messages(response):
    """Assert that response contains no messages."""
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 0, (
        f"Expected no messages, got: {[m.message for m in messages]}"
    )


def get_first_message(response):
    """Get first message from response or None."""
    messages = list(get_messages(response.wsgi_request))
    return messages[0].message if messages else None


# Common test data builders
def build_trip_data(title="Test Trip", destination="Test City", **kwargs):
    """Build common trip form data."""
    data = {
        "title": title,
        "destination": destination,
        "description": kwargs.get("description", ""),
        "start_date": kwargs.get("start_date", date.today()),
        "end_date": kwargs.get("end_date", date.today() + timedelta(days=3)),
    }
    data.update(kwargs)
    return data


def build_transport_data(**kwargs):
    """Build common transport form data."""
    data = {
        "type": kwargs.get("type", 1),
        "origin_city": kwargs.get("origin_city", "Milan"),
        "origin_address": kwargs.get("origin_address", "Central Station"),
        "destination_city": kwargs.get("destination_city", "Rome"),
        "destination_address": kwargs.get("destination_address", "Termini"),
        "start_time": kwargs.get("start_time", "10:00"),
        "end_time": kwargs.get("end_time", "12:00"),
        "company": kwargs.get("company", ""),
        "website": kwargs.get("website", ""),
    }
    return data


def build_experience_data(**kwargs):
    """Build common experience form data."""
    data = {
        "name": kwargs.get("name", "Walking Tour"),
        "type": kwargs.get("type", 1),
        "address": kwargs.get("address", "Starting Point"),
        "start_time": kwargs.get("start_time", "14:00"),
        "duration": kwargs.get("duration", "120"),
        "website": kwargs.get("website", ""),
    }
    return data


def build_meal_data(**kwargs):
    """Build common meal form data."""
    data = {
        "name": kwargs.get("name", "Restaurant"),
        "address": kwargs.get("address", "Main Street"),
        "start_time": kwargs.get("start_time", "19:00"),
        "duration": kwargs.get("duration", "90"),
        "website": kwargs.get("website", ""),
    }
    return data


def build_stay_data(**kwargs):
    """Build common stay form data."""
    data = {
        "name": kwargs.get("name", "Hotel"),
        "address": kwargs.get("address", "Hotel Street"),
        "check_in": kwargs.get("check_in", date.today()),
        "check_out": kwargs.get("check_out", date.today()),
        "website": kwargs.get("website", ""),
    }
    return data
