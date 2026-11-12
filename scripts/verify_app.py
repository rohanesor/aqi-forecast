"""Headless Streamlit end-to-end smoke verification. Requires generated artifacts."""
from streamlit.testing.v1 import AppTest


def by_label(elements, label):
    return next(element for element in elements if element.label == label)


at = AppTest.from_file("app.py", default_timeout=60).run()
assert not at.exception, at.exception
city_select = by_label(at.selectbox, "City")
assert {"Delhi", "Chennai"}.issubset(set(city_select.options))

city_select.select("Delhi").run()
assert not at.exception, at.exception
page_text = "\n".join(x.value for x in [*at.markdown, *at.error, *at.warning, *at.success])
for label in ("DAY +1", "DAY +2", "DAY +3"):
    assert label in page_text, f"Missing {label} card"
assert "13 Nov 2026" in page_text and "15 Nov 2026" in page_text
assert "HIGH AQI ALERT" in page_text, "Demo Delhi should exercise the >200 alert"
assert "Delhi" in page_text

by_label(at.selectbox, "City").select("Chennai").run()
assert not at.exception, at.exception
text = "\n".join(x.value for x in [*at.markdown, *at.error, *at.warning, *at.success])
assert "Chennai" in text
assert "HIGH AQI ALERT" not in text
print("Verified city updates, all three dated cards, and both >200 alert states.")
