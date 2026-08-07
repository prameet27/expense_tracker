import bisect

LEVEL_COLORS = {
    "high": "#c0392b",
    "medium": "#d68910",
    "low": "#1e8449",
}

CATEGORY_COLORS = [
    "#3498db", "#e67e22", "#9b59b6", "#1abc9c", "#e74c3c", "#2ec71", "#f1c40f", "#34495e", "#d35400"
]

def classify_level(value, sorted_values):
    n = len(sorted_values)
    if n <= 1:
        return "medium"

    lo = bisect.bisect_left(sorted_values, value)
    hi = bisect.bisect_right(sorted_values, value)
    rank = (lo + hi) / 2
    pct = rank / n
    if pct >= 2/3:
        return "high"
    elif pct >= 1/3:
        return "medium"
    else:
        return "low"