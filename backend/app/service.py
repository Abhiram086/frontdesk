import secrets
from datetime import datetime, timezone
from fastapi import HTTPException

from .clocks import (
    pause_clocks,
    reprioritise,
    restart_resolution,
    resume_clocks,
    settle,
    start_clock,
    stop_clock,
    used_minutes,
)
from .events import log_event
from .sla import AUTOCLOSE_MIN, REOPEN_WINDOW_MIN, working_minutes_between


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_holidays(cur) -> set:
    cur.execute("SELECT day FROM holidays")
    return {r["day"] for r in cur.fetchall()}


def lock_ticket(cur, tid: int) -> dict:
    # Row-level lock ensures two mutations on the same ticket run sequentially
    cur.execute("SELECT * FROM tickets WHERE id = %s FOR UPDATE", (tid,))
    t = cur.fetchone()
    if not t:
        raise HTTPException(404, "Ticket not found")
    return t


def require_assignee(t: dict, user: dict):
    # Closes INC-0291 completely: only the assigned agent can act on a ticket
    if t["assignee_id"] != user["id"]:
        raise HTTPException(403, "Only the assigned agent can do this")


# --- Create & Claim ---

def create_ticket(cur, name, email, subject, body, priority, follows=None, now=None):
    now = now or utcnow()
    hol = load_holidays(cur)

    cur.execute(
        """
        INSERT INTO tickets (public_token, customer_name, customer_email, subject,
                             priority, follows_ticket_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (secrets.token_urlsafe(24), name, email, subject, priority, follows, now),
    )
    t = cur.fetchone()

    cur.execute(
        """
        INSERT INTO messages (ticket_id, author_type, body, created_at)
        VALUES (%s, 'customer', %s, %s)
        """,
        (t["id"], body, now),
    )

    for kind in ("response", "resolution"):
        start_clock(cur, t["id"], kind, priority, now, hol)

    log_event(
        cur,
        t["id"],
        "customer",
        "ticket_created",
        {"priority": priority, "follows": follows},
        now,
    )
    return t


def claim_ticket(cur, tid: int, user: dict, now=None):
    now = now or utcnow()
    # Atomic claim (INC-0291): database guarantees only one agent wins
    cur.execute(
        """
        UPDATE tickets
        SET assignee_id = %s, status = 'open'
        WHERE id = %s AND assignee_id IS NULL AND status = 'new'
        RETURNING *
        """,
        (user["id"], tid),
    )
    t = cur.fetchone()
    if not t:
        raise HTTPException(409, "This ticket was already taken")

    log_event(cur, tid, f"agent:{user['id']}", "claimed", {"agent": user["name"]}, now)
    return t


# --- Agent Replies & Internal Notes ---

def agent_reply(cur, tid: int, user: dict, body: str, wait_for_customer: bool = False, now=None):
    now = now or utcnow()
    hol = load_holidays(cur)
    t = lock_ticket(cur, tid)
    require_assignee(t, user)

    if t["status"] not in ("open", "waiting_customer"):
        raise HTTPException(409, "Ticket is not open")

    cur.execute(
        """
        INSERT INTO messages (ticket_id, author_type, author_id, body, created_at)
        VALUES (%s, 'agent', %s, %s, %s)
        RETURNING id
        """,
        (tid, user["id"], body, now),
    )
    msg_id = cur.fetchone()["id"]
    log_event(cur, tid, f"agent:{user['id']}", "agent_reply", {"message_id": msg_id}, now)

    # First public reply stops the response clock
    stop_clock(cur, tid, "response", now, hol)

    if wait_for_customer and t["status"] != "waiting_customer":
        cur.execute(
            "UPDATE tickets SET status = 'waiting_customer', waiting_since = %s WHERE id = %s",
            (now, tid),
        )
        pause_clocks(cur, tid, now, hol)
        log_event(
            cur, tid, f"agent:{user['id']}", "status_changed", {"to": "waiting_customer"}, now
        )


def add_note(cur, tid: int, user: dict, body: str, now=None):
    now = now or utcnow()
    t = lock_ticket(cur, tid)
    require_assignee(t, user)

    cur.execute(
        """
        INSERT INTO internal_notes (ticket_id, author_id, body, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (tid, user["id"], body, now),
    )
    note_id = cur.fetchone()["id"]
    # Store only the note ID in events—never the private note text (INC-0304)
    log_event(cur, tid, f"agent:{user['id']}", "note_added", {"note_id": note_id}, now)


# --- Customer Actions ---

def customer_reply(cur, token: str, body: str, now=None):
    now = now or utcnow()
    hol = load_holidays(cur)

    cur.execute("SELECT id FROM tickets WHERE public_token = %s", (token,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")

    t = lock_ticket(cur, row["id"])
    expired = (
        t["status"] == "resolved"
        and working_minutes_between(t["resolved_at"], now, hol) > REOPEN_WINDOW_MIN
    )

    # R5: replying to a closed or expired ticket starts a fresh linked ticket
    if t["status"] == "closed" or expired:
        return create_ticket(
            cur,
            t["customer_name"],
            t["customer_email"],
            f"Follow-up: {t['subject']}",
            body,
            t["priority"],
            follows=t["id"],
            now=now,
        )

    cur.execute(
        """
        INSERT INTO messages (ticket_id, author_type, body, created_at)
        VALUES (%s, 'customer', %s, %s)
        """,
        (t["id"], body, now),
    )
    log_event(cur, t["id"], "customer", "customer_reply", {}, now)

    if t["status"] == "waiting_customer":
        cur.execute(
            "UPDATE tickets SET status = 'open', waiting_since = NULL WHERE id = %s",
            (t["id"],),
        )
        resume_clocks(cur, t["id"], now, hol)
        log_event(cur, t["id"], "customer", "status_changed", {"to": "open"}, now)
    elif t["status"] == "resolved":
        do_reopen(cur, t, "customer", now, hol)

    return t


# --- Resolve, Reopen, Priority, Close ---

def resolve_ticket(cur, tid: int, user: dict, now=None):
    now = now or utcnow()
    hol = load_holidays(cur)
    t = lock_ticket(cur, tid)
    require_assignee(t, user)

    if t["status"] not in ("open", "waiting_customer"):
        raise HTTPException(409, "Ticket is not open")

    stop_clock(cur, tid, "response", now, hol)
    stop_clock(cur, tid, "resolution", now, hol)
    cur.execute(
        "UPDATE tickets SET status = 'resolved', resolved_at = %s, waiting_since = NULL WHERE id = %s",
        (now, tid),
    )
    log_event(cur, tid, f"agent:{user['id']}", "resolved", {}, now)


def do_reopen(cur, t: dict, actor: str, now, hol: set):
    if t["status"] != "resolved":
        raise HTTPException(409, "Only resolved tickets can be reopened")
    if working_minutes_between(t["resolved_at"], now, hol) > REOPEN_WINDOW_MIN:
        raise HTTPException(409, "Reopen window is over. Please create a new ticket.")

    cur.execute("UPDATE tickets SET status = 'open', resolved_at = NULL WHERE id = %s", (t["id"],))
    restart_resolution(cur, t["id"], t["priority"], now, hol)
    log_event(cur, t["id"], actor, "reopened", {}, now)


def reopen_ticket(cur, tid: int, user: dict, now=None):
    now = now or utcnow()
    hol = load_holidays(cur)
    t = lock_ticket(cur, tid)
    require_assignee(t, user)
    do_reopen(cur, t, f"agent:{user['id']}", now, hol)


def change_priority(cur, tid: int, user: dict, new_priority: str, now=None):
    now = now or utcnow()
    hol = load_holidays(cur)
    t = lock_ticket(cur, tid)
    require_assignee(t, user)

    if t["status"] in ("resolved", "closed") or new_priority == t["priority"]:
        raise HTTPException(409, "Priority cannot be changed now")

    cur.execute("UPDATE tickets SET priority = %s WHERE id = %s", (new_priority, tid))
    reprioritise(cur, tid, new_priority, now, hol)
    log_event(
        cur,
        tid,
        f"agent:{user['id']}",
        "priority_changed",
        {"from": t["priority"], "to": new_priority},
        now,
    )


def close_ticket(cur, t: dict, reason: str, now, hol: set):
    for kind in ("response", "resolution"):
        stop_clock(cur, t["id"], kind, now, hol)
    cur.execute(
        "UPDATE tickets SET status = 'closed', closed_at = %s, close_reason = %s WHERE id = %s",
        (now, reason, t["id"]),
    )
    log_event(cur, t["id"], "system", "closed", {"reason": reason}, now)


# --- Background Sweep (runs every 60s) ---

def run_sweep(now=None):
    from .db import tx

    now = now or utcnow()
    with tx() as cur:
        hol = load_holidays(cur)

        # R4: Auto-close tickets waiting on customer for 5+ working days
        cur.execute("SELECT * FROM tickets WHERE status = 'waiting_customer' FOR UPDATE SKIP LOCKED")
        for t in cur.fetchall():
            if working_minutes_between(t["waiting_since"], now, hol) >= AUTOCLOSE_MIN:
                close_ticket(cur, t, "customer_silent", now, hol)

        # R5: Close resolved tickets once the 5-working-day reopen window expires
        cur.execute("SELECT * FROM tickets WHERE status = 'resolved' FOR UPDATE SKIP LOCKED")
        for t in cur.fetchall():
            if working_minutes_between(t["resolved_at"], now, hol) > REOPEN_WINDOW_MIN:
                close_ticket(cur, t, "reopen_window_over", now, hol)

        # R11: Permanently log newly breached SLA clocks
        cur.execute(
            """
            SELECT * FROM sla_clocks
            WHERE stopped_at IS NULL
              AND running_since IS NOT NULL
              AND breached_at IS NULL
              AND due_at < %s
            FOR UPDATE SKIP LOCKED
            """,
            (now,),
        )
        for c in cur.fetchall():
            settle(cur, c, used_minutes(c, now, hol), now)
            