from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest


def test_double_claim(client, agent_tokens, new_ticket):
    # INC-0291: Two agents click "Take" at the exact same moment -> one 200, one 409
    def claim(tok):
        return client.post(
            f"/api/tickets/{new_ticket.id}/claim",
            headers={"Authorization": f"Bearer {tok}"},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as ex:
        results = sorted(ex.map(claim, agent_tokens[:2]))
    assert results == [200, 409]


def test_non_assignee_blocked(client, agent_tokens, claimed_ticket):
    # INC-0291 extra: Agent 2 cannot reply, note, or resolve Agent 1's ticket
    other_headers = {"Authorization": f"Bearer {agent_tokens[1]}"}
    tid = claimed_ticket.id

    assert client.post(
        f"/api/tickets/{tid}/reply", json={"body": "hi"}, headers=other_headers
    ).status_code == 403
    assert client.post(
        f"/api/tickets/{tid}/notes", json={"body": "internal"}, headers=other_headers
    ).status_code == 403
    assert client.post(
        f"/api/tickets/{tid}/resolve", headers=other_headers
    ).status_code == 403


def test_note_never_reaches_customer(client, agent_token, claimed_ticket):
    # INC-0304: Private note text must never appear in public endpoints or event logs
    secret = "SECRET-NOTE-9f3a"
    headers = {"Authorization": f"Bearer {agent_token}"}

    res = client.post(
        f"/api/tickets/{claimed_ticket.id}/notes",
        json={"body": secret},
        headers=headers,
    )
    assert res.status_code == 200

    pub_view = client.get(f"/api/public/tickets/{claimed_ticket.token}")
    pub_reply = client.post(
        f"/api/public/tickets/{claimed_ticket.token}/reply",
        json={"body": "Any update?"},
    )
    assert secret not in pub_view.text
    assert secret not in pub_reply.text

    # Audit events store only note_id, never the note text
    events = client.get(f"/api/tickets/{claimed_ticket.id}/events", headers=headers)
    assert secret not in events.text


def test_audit_log_is_append_only(client, agent_token, claimed_ticket, db):
    # INC-0318: Ensure rows exist in all three append-only tables, then try mutating them
    headers = {"Authorization": f"Bearer {agent_token}"}
    client.post(
        f"/api/tickets/{claimed_ticket.id}/notes",
        json={"body": "Audit test note"},
        headers=headers,
    )

    for sql in (
        "UPDATE events SET type = 'tampered'",
        "DELETE FROM events",
        "TRUNCATE events",
        "UPDATE messages SET body = 'tampered'",
        "DELETE FROM messages",
        "TRUNCATE messages",
        "UPDATE internal_notes SET body = 'tampered'",
        "DELETE FROM internal_notes",
        "TRUNCATE internal_notes",
    ):
        with pytest.raises(psycopg.errors.RaiseException):
            db.execute(sql)