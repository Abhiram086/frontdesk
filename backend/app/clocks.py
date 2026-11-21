from .events import log_event
from .sla import add_working_minutes, target_minutes, working_minutes_between


def start_clock(cur, tid: int, kind: str, priority: str, now, hol: set):
    target = target_minutes(priority, kind, now, hol)
    due = add_working_minutes(now, target, hol)
    cur.execute(
        """
        INSERT INTO sla_clocks (ticket_id, kind, started_at, target_min, running_since, due_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (tid, kind, now, target, now, due),
    )


def open_clocks(cur, tid: int):
    # Lock open clock rows so concurrent updates serialize cleanly
    cur.execute(
        "SELECT * FROM sla_clocks WHERE ticket_id = %s AND stopped_at IS NULL FOR UPDATE",
        (tid,),
    )
    return cur.fetchall()


def used_minutes(c: dict, now, hol: set) -> float:
    used = float(c["elapsed_min"])
    if c["running_since"]:
        used += working_minutes_between(c["running_since"], now, hol)
    return used


def remaining(c: dict, now, hol: set) -> float:
    # Negative means the clock is late by that many working minutes
    return c["target_min"] - used_minutes(c, now, hol)


def late_reason(kind: str, assignee: str | None) -> str:
    if assignee is None:
        return "Nobody claimed the ticket in time"
    if kind == "response":
        return f"Claimed by {assignee} but no reply was sent in time"
    return f"Claimed by {assignee} but not resolved in time"


def settle(cur, c: dict, used: float, now):
    """Record an SLA breach once with its reason when a clock is paused, stopped, or swept."""
    if used <= c["target_min"] or c["breached_at"]:
        return

    cur.execute(
        """
        SELECT u.name
        FROM tickets t
        LEFT JOIN users u ON u.id = t.assignee_id
        WHERE t.id = %s
        """,
        (c["ticket_id"],),
    )
    who = cur.fetchone()["name"]

    cur.execute(
        "UPDATE sla_clocks SET breached_at = %s WHERE ticket_id = %s AND kind = %s",
        (c["due_at"] or now, c["ticket_id"], c["kind"]),
    )
    log_event(
        cur,
        c["ticket_id"],
        "system",
        "sla_breached",
        {
            "kind": c["kind"],
            "target_min": c["target_min"],
            "late_by_min": round(used - c["target_min"]),
            "reason": late_reason(c["kind"], who),
        },
        now,
    )

def stop_clock(cur, tid: int, kind: str, now, hol: set):
    for c in open_clocks(cur, tid):
        if c["kind"] != kind:
            continue
        used = used_minutes(c, now, hol)
        settle(cur, c, used, now)
        # If an earlier sweep already logged sla_breached, record the final overdue time on stop
        if c["breached_at"] and used > c["target_min"]:
            log_event(
                cur,
                tid,
                "system",
                "sla_final",
                {
                    "kind": kind,
                    "target_min": c["target_min"],
                    "late_by_min": round(used - c["target_min"]),
                },
                now,
            )
        cur.execute(
            """
            UPDATE sla_clocks
            SET elapsed_min = %s, running_since = NULL, due_at = NULL, stopped_at = %s
            WHERE ticket_id = %s AND kind = %s
            """,
            (used, now, tid, kind),
        )

def pause_clocks(cur, tid: int, now, hol: set):
    for c in open_clocks(cur, tid):
        if c["running_since"] is None:
            continue
        used = used_minutes(c, now, hol)
        settle(cur, c, used, now)
        cur.execute(
            """
            UPDATE sla_clocks
            SET elapsed_min = %s, running_since = NULL, due_at = NULL
            WHERE ticket_id = %s AND kind = %s
            """,
            (used, tid, c["kind"]),
        )


def resume_clocks(cur, tid: int, now, hol: set):
    for c in open_clocks(cur, tid):
        if c["running_since"] is not None:
            continue
        left = max(c["target_min"] - float(c["elapsed_min"]), 0)
        due = add_working_minutes(now, left, hol)
        cur.execute(
            """
            UPDATE sla_clocks
            SET running_since = %s, due_at = %s
            WHERE ticket_id = %s AND kind = %s
            """,
            (now, due, tid, c["kind"]),
        )


def reprioritise(cur, tid: int, new_priority: str, now, hol: set):
    """Decision R7: keep start time and used minutes, apply the new priority's target."""
    for c in open_clocks(cur, tid):
        used = used_minutes(c, now, hol)
        target = target_minutes(new_priority, c["kind"], c["started_at"], hol)
        running = c["running_since"] is not None
        due = add_working_minutes(now, max(target - used, 0), hol) if running else None
        cur.execute(
            """
            UPDATE sla_clocks
            SET target_min = %s, elapsed_min = %s, running_since = %s, due_at = %s
            WHERE ticket_id = %s AND kind = %s
            """,
            (target, used, now if running else None, due, tid, c["kind"]),
        )


def restart_resolution(cur, tid: int, priority: str, now, hol: set):
    """Reopen rule: restart only the resolution clock from zero; response stays stopped."""
    target = target_minutes(priority, "resolution", now, hol)
    due = add_working_minutes(now, target, hol)
    cur.execute(
        """
        UPDATE sla_clocks
        SET started_at = %s, target_min = %s, elapsed_min = 0,
            running_since = %s, due_at = %s, stopped_at = NULL, breached_at = NULL
        WHERE ticket_id = %s AND kind = 'resolution'
        """,
        (now, target, now, due, tid),
    )