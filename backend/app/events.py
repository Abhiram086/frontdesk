import json


def log_event(cur, tid: int, actor: str, event_type: str, payload: dict, now):
    """Append an immutable audit record to the events table."""
    cur.execute(
        """
        INSERT INTO events (ticket_id, at, actor, type, payload)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (tid, now, actor, event_type, json.dumps(payload)),
    )