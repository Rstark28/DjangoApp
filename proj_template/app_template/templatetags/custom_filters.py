# app_template/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter(name='divide')
def divide(value, arg):
    try:
        result = int(value) / int(arg) * 100
        return round(result, 1)
    except (ValueError, ZeroDivisionError):
        return None
    
@register.filter
def to(value, arg):
    return range(value, arg + 1)
