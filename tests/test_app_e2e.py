import pytest
from streamlit.testing.v1 import AppTest


def by_label(elements, label):
    return next(element for element in elements if element.label == label)


def page_text(at):
    return "\n".join(x.value for x in [*at.markdown, *at.error, *at.warning, *at.success])


@pytest.mark.e2e
def test_city_selection_cards_dates_and_alert():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    assert not at.exception
    city = by_label(at.selectbox, "City")
    assert {"Delhi", "Chennai"}.issubset(set(city.options))

    city.select("Delhi").run()
    text = page_text(at)
    assert all(label in text for label in ("DAY +1", "DAY +2", "DAY +3"))
    assert "13 Nov 2026" in text and "15 Nov 2026" in text
    assert "HIGH AQI ALERT" in text

    by_label(at.selectbox, "City").select("Chennai").run()
    text = page_text(at)
    assert "Chennai" in text
    assert "HIGH AQI ALERT" not in text
