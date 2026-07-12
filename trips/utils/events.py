from django.http import Http404

from trips.models import Event, Experience, Meal


def build_categorized_event(category, **fields):
    """Build the proper STI child (Experience/Meal) for the given category.

    The map place-search and AI-suggestion accept flows must create a real
    Experience/Meal so every event has its STI child row; a plain ``Event``
    would break the event-detail modal (see get_event_instance).
    """
    model = {Event.Category.EXPERIENCE: Experience, Event.Category.MEAL: Meal}
    return model[category](**fields)


def get_event_instance(event):
    """
    Get the specific event instance based on its category.
    """
    if event.category == 2:  # Experience
        return event.experience
    elif event.category == 3:  # Meal
        return event.meal
    else:
        raise Http404("Invalid event category")
