from __future__ import annotations

import math

CATEGORIES = [
    (0, 50, "Good", "#009966"),
    (51, 100, "Satisfactory", "#66CC66"),
    (101, 200, "Moderate", "#F2D600"),
    (201, 300, "Poor", "#FF9900"),
    (301, 400, "Very Poor", "#E53935"),
    (401, math.inf, "Severe", "#990000"),
]


def aqi_category(value: float) -> str:
    if value is None or not math.isfinite(float(value)):
        return "Unavailable"
    value = max(0.0, float(value))
    for low, high, label, _ in CATEGORIES:
        if low <= value <= high:
            return label
    return "Severe"


def category_colour(value: float) -> str:
    label = aqi_category(value)
    return next((colour for _, _, name, colour in CATEGORIES if name == label), "#808080")
