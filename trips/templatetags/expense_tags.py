from django import template
from django.contrib.contenttypes.models import ContentType

from trips.models import Event, Expense

register = template.Library()

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£"}


@register.filter
def money(amount, currency="EUR"):
    """Format a Decimal amount with its currency symbol, e.g. '€ 12.00'."""
    if amount is None:
        amount = 0
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    return f"{symbol} {amount:.2f}"


@register.simple_tag
def linked_expense(obj):
    """Return the Expense linked to obj (Event/Stay/MainTransfer), or None."""
    if obj is None or obj.pk is None:
        return None
    model = Event if isinstance(obj, Event) else type(obj)
    ct = ContentType.objects.get_for_model(model)
    return Expense.objects.filter(content_type=ct, object_id=obj.pk).first()
