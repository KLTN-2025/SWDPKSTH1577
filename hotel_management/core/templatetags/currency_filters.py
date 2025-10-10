from django import template

register = template.Library()

@register.filter
def format_currency(value):
    try:
        value = int(float(value))  
        return "{:,.0f}".format(value).replace(",", ".")
    except (ValueError, TypeError):
        return value