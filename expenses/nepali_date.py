import nepali_datetime

def to_bs_date(ad_date):
    if ad_date is None:
        return None

    try:
        return nepali_datetime.date.from_datetime_date(ad_date)
    except (ValueError, OverflowError):
        return None


def to_bs_string(ad_date, fmt="%d %B %Y"):
    bs = to_bs_date(ad_date)
    if bs is None:
        return ""
    return bs.strftime(fmt)

def bs_month_range_label(ad_date_start, ad_date_end):
    start = to_bs_date(ad_date_start)
    end = to_bs_date(ad_date_end)

    if not start or not end:
        return ""

    if (start.year, start.month) == (end.year, end.month):
        return f"{start.strftime('%B')} {start.day}-{end.day}, {start.year} BS"
    return f"{start.strftime('%d %B %Y')} - {end.strftime('%d %B %Y')} BS"