from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.sla import (
    add_working_minutes,
    target_minutes,
    working_minutes_between,
)

IST = ZoneInfo("Asia/Kolkata")
HOL = {date(2026, 12, 25)}  # Christmas (Friday)


def at(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=IST)


def test_friday_evening_not_late_on_sunday():
    # Ticket raised Friday 18:00: only 30 working min pass before weekend
    fri = at(2026, 11, 20, 18, 0)
    assert working_minutes_between(fri, at(2026, 11, 22, 10, 0), HOL) == 30
    # 120-min critical response due Monday 11:00 (30m Fri + 90m Mon)
    assert add_working_minutes(fri, 120, HOL) == at(2026, 11, 23, 11, 0)


def test_holiday_and_weekend_skipped():
    # Thursday Dec 24 17:30 + 270m (60m Thu, skips Fri Christmas + weekend, 210m Mon)
    start = at(2026, 12, 24, 17, 30)
    assert add_working_minutes(start, 270, HOL) == at(2026, 12, 28, 13, 0)


def test_critical_same_day_target():
    # Monday 14:00 -> due 18:30 same day (270 min)
    assert target_minutes("critical", "resolution", at(2026, 11, 23, 14, 0), HOL) == 270
    # Monday 19:00 -> starts Tuesday 09:30, due Tuesday 18:30 (540 min)
    assert target_minutes("critical", "resolution", at(2026, 11, 23, 19, 0), HOL) == 540


def test_pause_resume_arithmetic():
    # Low response (540m) with 120m already used -> 420m left
    left = 540 - 120
    assert add_working_minutes(at(2026, 11, 27, 11, 0), left, HOL) == at(2026, 11, 27, 18, 0)