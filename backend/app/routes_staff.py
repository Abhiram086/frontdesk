from fastapi import APIRouter, Depends, HTTPException

from .auth import current_user, manager_only
from .clocks import remaining
from .db import tx
from .schemas import Note, PriorityChange, Reply
from . import service as sv

router = APIRouter(prefix="/api")


def _clock_state(c: dict) -> str:
    if c["stopped_at"]:
        return "stopped"
    return "running" if c["running_since"] else "paused"


@router.get("/tickets")
def list_tickets(view: str = "mine", user: dict = Depends(current_user)):
    if view not in ("mine", "unassigned", "all"):
        raise HTTPException(400, "Invalid view")
    if view == "all" and user["role"] != "manager":
        raise HTTPException(403, "Managers only")

    where = {
        "mine": "t.assignee_id = %(uid)s AND t.status <> 'closed'",
        "unassigned": "t.assignee_id IS NULL AND t.status = 'new'",
        "all": "t.status <> 'closed'",
    }[view]

    now = sv.utcnow()
    with tx() as cur:
        hol = sv.load_holidays(cur)
        cur.execute(
            f"""
            SELECT t.id, t.subject, t.customer_name, t.priority, t.status, t.created_at,
                   u.name AS assignee
            FROM tickets t
            LEFT JOIN users u ON u.id = t.assignee_id
            WHERE {where}
            """,
            {"uid": user["id"]},
        )
        rows = cur.fetchall()
        if not rows:
            return []

        cur.execute(
            "SELECT * FROM sla_clocks WHERE ticket_id = ANY(%s)",
            ([r["id"] for r in rows],),
        )
        by_ticket: dict[int, list] = {}
        for c in cur.fetchall():
            by_ticket.setdefault(c["ticket_id"], []).append(c)

    for r in rows:
        r["clocks"] = [
            {
                "kind": c["kind"],
                "state": _clock_state(c),
                "remaining_min": round(remaining(c, now, hol)),
            }
            for c in by_ticket.get(r["id"], [])
        ]
        r["late"] = any(
            c["state"] == "running" and c["remaining_min"] < 0 for c in r["clocks"]
        )
        r["waiting"] = r["status"] == "waiting_customer"

    # Show late tickets at the top, then sort by tightest active deadline
    rows.sort(
        key=lambda r: (
            not r["late"],
            min(
                [c["remaining_min"] for c in r["clocks"] if c["state"] != "stopped"]
                or [10**9]
            ),
        )
    )
    return rows


@router.get("/tickets/{tid}")
def detail(tid: int, user: dict = Depends(current_user)):
    now = sv.utcnow()
    with tx() as cur:
        hol = sv.load_holidays(cur)
        cur.execute(
            """
            SELECT t.*, u.name AS assignee
            FROM tickets t
            LEFT JOIN users u ON u.id = t.assignee_id
            WHERE t.id = %s
            """,
            (tid,),
        )
        t = cur.fetchone()
        if not t:
            raise HTTPException(404, "Ticket not found")

        # Merge customer/agent messages and team-only notes chronologically for staff view
        cur.execute(
            """
            SELECT 'message' AS src, m.id, m.author_type AS kind, u.name AS author,
                   m.body, m.created_at
            FROM messages m
            LEFT JOIN users u ON u.id = m.author_id
            WHERE m.ticket_id = %(t)s
            UNION ALL
            SELECT 'note' AS src, n.id, 'note' AS kind, u.name AS author,
                   n.body, n.created_at
            FROM internal_notes n
            JOIN users u ON u.id = n.author_id
            WHERE n.ticket_id = %(t)s
            ORDER BY created_at
            """,
            {"t": tid},
        )
        thread = cur.fetchall()

        cur.execute("SELECT * FROM sla_clocks WHERE ticket_id = %s", (tid,))
        clocks = [
            {
                "kind": c["kind"],
                "target_min": c["target_min"],
                "state": _clock_state(c),
                "remaining_min": round(remaining(c, now, hol)),
            }
            for c in cur.fetchall()
        ]

    t.pop("public_token", None)  # Staff do not need the customer's secret portal token
    return {
        "ticket": t,
        "thread": thread,
        "clocks": clocks,
        "is_assignee": t["assignee_id"] == user["id"],
    }


@router.post("/tickets/{tid}/claim")
def claim(tid: int, user: dict = Depends(current_user)):
    with tx() as cur:
        sv.claim_ticket(cur, tid, user)
    return {"ok": True}


@router.post("/tickets/{tid}/reply")
def reply(tid: int, data: Reply, user: dict = Depends(current_user)):
    with tx() as cur:
        sv.agent_reply(cur, tid, user, data.body, data.wait_for_customer)
    return {"ok": True}


@router.post("/tickets/{tid}/notes")
def note(tid: int, data: Note, user: dict = Depends(current_user)):
    with tx() as cur:
        sv.add_note(cur, tid, user, data.body)
    return {"ok": True}


@router.post("/tickets/{tid}/resolve")
def resolve(tid: int, user: dict = Depends(current_user)):
    with tx() as cur:
        sv.resolve_ticket(cur, tid, user)
    return {"ok": True}


@router.post("/tickets/{tid}/reopen")
def reopen(tid: int, user: dict = Depends(current_user)):
    with tx() as cur:
        sv.reopen_ticket(cur, tid, user)
    return {"ok": True}


@router.post("/tickets/{tid}/priority")
def priority(tid: int, data: PriorityChange, user: dict = Depends(current_user)):
    with tx() as cur:
        sv.change_priority(cur, tid, user, data.priority)
    return {"ok": True}


@router.get("/tickets/{tid}/events")
def events(tid: int, user: dict = Depends(current_user)):
    with tx() as cur:
        cur.execute("SELECT 1 FROM tickets WHERE id = %s", (tid,))
        if not cur.fetchone():
            raise HTTPException(404, "Ticket not found")
        cur.execute(
            "SELECT id, at, actor, type, payload FROM events WHERE ticket_id = %s ORDER BY id",
            (tid,),
        )
        return cur.fetchall()


@router.get("/reports/late")
def late_report(user: dict = Depends(manager_only)):
    with tx() as cur:
        cur.execute(
            """
            SELECT e.at, e.ticket_id, t.subject, t.priority, t.status,
                   u.name AS assignee,
                   e.payload->>'kind' AS clock,
                   (e.payload->>'target_min')::int AS target_min,
                   COALESCE(
                       (f.payload->>'late_by_min')::int,
                       (e.payload->>'late_by_min')::int
                   ) AS late_by_min,
                   e.payload->>'reason' AS reason
            FROM events e
            JOIN tickets t ON t.id = e.ticket_id
            LEFT JOIN users u ON u.id = t.assignee_id
            LEFT JOIN LATERAL (
                SELECT payload
                FROM events f
                WHERE f.ticket_id = e.ticket_id
                  AND f.type = 'sla_final'
                  AND f.payload->>'kind' = e.payload->>'kind'
                  AND f.id > e.id
                ORDER BY f.id
                LIMIT 1
            ) f ON true
            WHERE e.type = 'sla_breached'
            ORDER BY e.at DESC
            """
        )
        return cur.fetchall()