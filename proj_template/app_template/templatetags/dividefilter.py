
from django import template

register = template.Library()

@register.filter(name='divide')
def divide(value, arg):
    try:
        return int(value) / int(arg) * 100
    except (ValueError, ZeroDivisionError):
        return None