from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
OPEN = time(9, 30)
CLOSE = time(18, 30)

DAY = 540                 # 9 working hours per day (09:30 to 18:30)
REOPEN_WINDOW_MIN = 5 * DAY
AUTOCLOSE_MIN = 5 * DAY

TARGETS = {
    "critical": {"response": 120, "resolution": "end_of_day"},
    "medium": {"response": 270, "resolution": 3 * DAY},
    "low": {"response": DAY, "resolution": 5 * DAY},
}


def open_dt(d: date) -> datetime:
    return datetime.combine(d, OPEN, tzinfo=IST)


def close_dt(d: date) -> datetime:
    return datetime.combine(d, CLOSE, tzinfo=IST)


def is_workday(d: date, hol: set[date]) -> bool:
    # Monday=0 .. Friday=4; Saturday=5, Sunday=6
    return d.weekday() < 5 and d not in hol


def next_workday(d: date, hol: set[date]) -> date:
    d += timedelta(days=1)
    while not is_workday(d, hol):
        d += timedelta(days=1)
    return d


def snap_forward(dt: datetime, hol: set[date]) -> datetime:
    """Return the nearest moment at or after dt that falls inside working hours."""
    dt = dt.astimezone(IST)
    d = dt.date()
    if is_workday(d, hol):
        if dt < open_dt(d):
            return open_dt(d)
        if dt < close_dt(d):
            return dt
    return open_dt(next_workday(d, hol))


def add_working_minutes(start: datetime, minutes: float, hol: set[date]) -> datetime:
    """Add working minutes to start, skipping nights, weekends, and holidays."""
    cur = snap_forward(start, hol)
    left = float(minutes)

    while True:
        avail = (close_dt(cur.date()) - cur).total_seconds() / 60
        if left <= avail:
            return cur + timedelta(minutes=left)
        left -= avail
        cur = open_dt(next_workday(cur.date(), hol))


def working_minutes_between(a: datetime, b: datetime, hol: set[date]) -> float:
    """Count how many working minutes elapsed between timestamps a and b."""
    a, b = a.astimezone(IST), b.astimezone(IST)
    if b <= a:
        return 0.0

    total = 0.0
    d = a.date()
    while d <= b.date():
        if is_workday(d, hol):
            s = max(a, open_dt(d))
            e = min(b, close_dt(d))
            if e > s:
                total += (e - s).total_seconds() / 60
        d += timedelta(days=1)
    return total


def target_minutes(priority: str, kind: str, started_at: datetime, hol: set[date]) -> int:
    """Return allowed working minutes for a clock based on priority and start time."""
    t = TARGETS[priority][kind]
    if t == "end_of_day":
        # Critical fix is due at 18:30 of the working day the clock starts
        s = snap_forward(started_at, hol)
        return round(working_minutes_between(s, close_dt(s.date()), hol))
    return t