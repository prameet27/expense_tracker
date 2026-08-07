from calendar import monthrange
from datetime import date

from django import template
from expenses.nepali_date import to_bs_string, bs_month_range_label

register = template.Library()

@register.filter(name="bs_date")
def bs_date(value, fmt="%d %B %Y"):
    return to_bs_string(value, fmt)

@register.simple_tag(name="bs_month_range")
def bs_month_range(year, month):
    if not year or not month:
        return ""

    start = date(int(year), int(month), 1)
    end = date(int(year), int(month), monthrange(int(year), int(month))[1])
    return bs_month_range_label(start, end)