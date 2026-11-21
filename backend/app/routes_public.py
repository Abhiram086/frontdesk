from fastapi import APIRouter, HTTPException

from .db import tx
from .schemas import NewTicket, Note, PublicMessage, PublicTicket
from .sla import REOPEN_WINDOW_MIN, working_minutes_between
from . import service as sv

router = APIRouter(prefix="/api/public")


def build_public(cur, token: str) -> PublicTicket:
    cur.execute(
        """
        SELECT id, subject, status, priority, created_at, resolved_at
        FROM tickets
        WHERE public_token = %s
        """,
        (token,),
    )
    t = cur.fetchone()
    if not t:
        raise HTTPException(404, "Not found")

    # Queries the messages table only—internal_notes is never touched (INC-0304)
    cur.execute(
        "SELECT author_type, body, created_at FROM messages WHERE ticket_id = %s ORDER BY created_at",
        (t["id"],),
    )
    msgs = [
        PublicMessage(
            author="you" if m["author_type"] == "customer" else "support",
            body=m["body"],
            at=m["created_at"],
        )
        for m in cur.fetchall()
    ]

    hol = sv.load_holidays(cur)
    can_reopen = (
        t["status"] == "resolved"
        and working_minutes_between(t["resolved_at"], sv.utcnow(), hol) <= REOPEN_WINDOW_MIN
    )
    return PublicTicket(
        subject=t["subject"],
        status=t["status"],
        priority=t["priority"],
        created_at=t["created_at"],
        can_reopen=can_reopen,
        messages=msgs,
    )


@router.post("/tickets")
def create(data: NewTicket):
    with tx() as cur:
        t = sv.create_ticket(
            cur, data.name, data.email, data.subject, data.body, data.priority
        )
    return {"token": t["public_token"]}


@router.get("/tickets/{token}", response_model=PublicTicket)
def view(token: str):
    with tx() as cur:
        return build_public(cur, token)


@router.post("/tickets/{token}/reply")
def reply(token: str, data: Note):
    with tx() as cur:
        t = sv.customer_reply(cur, token, data.body)
    # Token will be new if replying to a closed/expired ticket created a follow-up
    return {"token": t["public_token"]}


@router.post("/tickets/{token}/reopen")
def reopen(token: str):
    with tx() as cur:
        cur.execute("SELECT id FROM tickets WHERE public_token = %s", (token,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        t = sv.lock_ticket(cur, row["id"])
        sv.do_reopen(cur, t, "customer", sv.utcnow(), sv.load_holidays(cur))
    return {"ok": True}
    