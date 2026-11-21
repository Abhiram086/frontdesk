from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from app import service as sv
from app.clocks import remaining
from app.db import tx

IST = ZoneInfo("Asia/Kolkata")


def at(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=IST)


def _agent(cur):
    cur.execute("SELECT id, name, email, role FROM users WHERE email = 'agent1@arvo.test'")
    return cur.fetchone()


def test_priority_change_mid_ticket():
    # R7: Upgrade keeps elapsed time and can make clock late immediately; downgrade gives time back
    start = at(2026, 11, 16, 10, 0)  # Monday 10:00
    after_3h = at(2026, 11, 16, 13, 0)  # 180 working min used

    with tx() as cur:
        agent = _agent(cur)
        hol = sv.load_holidays(cur)
        t = sv.create_ticket(cur, "Asha", "asha@test", "Slow report", "Takes 20s", "low", now=start)
        sv.claim_ticket(cur, t["id"], agent, now=start)

        # Upgrade low (540m response) -> critical (120m response) after 180m used => -60m (late!)
        sv.change_priority(cur, t["id"], agent, "critical", now=after_3h)
        cur.execute("SELECT * FROM sla_clocks WHERE ticket_id = %s AND kind = 'response'", (t["id"],))
        resp_clock = cur.fetchone()
        assert round(remaining(resp_clock, after_3h, hol)) == -60

        # Downgrade critical -> medium (270m response) => +90m left
        sv.change_priority(cur, t["id"], agent, "medium", now=after_3h)
        cur.execute("SELECT * FROM sla_clocks WHERE ticket_id = %s AND kind = 'response'", (t["id"],))
        resp_clock = cur.fetchone()
        assert round(remaining(resp_clock, after_3h, hol)) == 90


def test_auto_close_after_silence():
    # R4: 4 working days silent stays waiting; 5 working days silent auto-closes
    mon = at(2026, 11, 2, 10, 0)
    fri_day4 = at(2026, 11, 6, 10, 0)   # 4 working days (2160 min)
    mon_day5 = at(2026, 11, 9, 10, 0)   # 5 working days (2700 min)

    with tx() as cur:
        agent = _agent(cur)
        t = sv.create_ticket(cur, "Binu", "binu@test", "Login issue", "Need help", "medium", now=mon)
        sv.claim_ticket(cur, t["id"], agent, now=mon)
        sv.agent_reply(cur, t["id"], agent, "Please share screenshot", wait_for_customer=True, now=mon)
        tid = t["id"]

    sv.run_sweep(now=fri_day4)
    with tx() as cur:
        cur.execute("SELECT status FROM tickets WHERE id = %s", (tid,))
        assert cur.fetchone()["status"] == "waiting_customer"

    sv.run_sweep(now=mon_day5)
    with tx() as cur:
        cur.execute("SELECT status, close_reason FROM tickets WHERE id = %s", (tid,))
        row = cur.fetchone()
        assert row["status"] == "closed"
        assert row["close_reason"] == "customer_silent"


def test_reopen_window_and_followup():
    # R5: Reopen on day 5 works; on day 6 reopen raises 409 and customer reply creates linked ticket
    mon = at(2026, 11, 2, 10, 0)
    day5 = at(2026, 11, 9, 10, 0)       # exactly 5 working days (2700 min) -> allowed
    day6 = at(2026, 11, 10, 10, 0)      # 6 working days (3240 min) -> expired

    with tx() as cur:
        agent = _agent(cur)
        t1 = sv.create_ticket(cur, "Deepa", "deepa@test", "Billing bug", "Wrong total", "low", now=mon)
        sv.claim_ticket(cur, t1["id"], agent, now=mon)
        sv.resolve_ticket(cur, t1["id"], agent, now=mon)
        sv.reopen_ticket(cur, t1["id"], agent, now=day5)

        cur.execute("SELECT status FROM tickets WHERE id = %s", (t1["id"],))
        assert cur.fetchone()["status"] == "open"

        # Resolve again at mon and try reopening on day 6
        t2 = sv.create_ticket(cur, "Deepa", "deepa@test", "Old bug", "Details", "low", now=mon)
        sv.claim_ticket(cur, t2["id"], agent, now=mon)
        sv.resolve_ticket(cur, t2["id"], agent, now=mon)

        with pytest.raises(HTTPException) as exc:
            sv.reopen_ticket(cur, t2["id"], agent, now=day6)
        assert exc.value.status_code == 409

        # Customer replying after day 6 creates a brand-new linked ticket
        followup = sv.customer_reply(cur, t2["public_token"], "Still broken", now=day6)
        assert followup["id"] != t2["id"]
        assert followup["follows_ticket_id"] == t2["id"]


def test_late_report_persists_after_resolve(client, manager_token):
    # R11: Breach stays in manager's Late Report with its reason even after ticket is resolved
    mon_10 = at(2026, 11, 2, 10, 0)
    mon_15 = at(2026, 11, 2, 15, 0)  # 300 min later -> breaches 120m critical response

    with tx() as cur:
        agent = _agent(cur)
        t = sv.create_ticket(cur, "Kiran", "kiran@test", "Site down", "502 error", "critical", now=mon_10)
        sv.claim_ticket(cur, t["id"], agent, now=mon_10)
        sv.resolve_ticket(cur, t["id"], agent, now=mon_15)
        tid = t["id"]

    res = client.get(
        "/api/reports/late",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert res.status_code == 200
    breaches = [r for r in res.json() if r["ticket_id"] == tid]
    assert len(breaches) >= 1
    assert breaches[0]["status"] == "resolved"
    assert "Agent 1" in breaches[0]["reason"]

def test_late_report_reflects_final_overdue_after_sweep(client, manager_token):
    # Sweeper catches a medium response 30m late, but agent replies 750m late -> report shows 750m
    mon_0930 = at(2026, 11, 2, 9, 30)   # 270m target -> due Mon 14:00
    mon_1430 = at(2026, 11, 2, 14, 30)  # 30m late (swept here)
    tue_1730 = at(2026, 11, 3, 17, 30)  # 750m late (agent finally replies)

    with tx() as cur:
        agent = _agent(cur)
        t = sv.create_ticket(
            cur, "Maya", "maya@test", "Delayed reply", "Need help", "medium", now=mon_0930
        )
        sv.claim_ticket(cur, t["id"], agent, now=mon_0930)
        tid = t["id"]

    sv.run_sweep(now=mon_1430)

    with tx() as cur:
        agent = _agent(cur)
        sv.agent_reply(
            cur, tid, agent, "Sorry for the delay", wait_for_customer=False, now=tue_1730
        )

    res = client.get(
        "/api/reports/late",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert res.status_code == 200
    breaches = [r for r in res.json() if r["ticket_id"] == tid and r["clock"] == "response"]
    assert len(breaches) == 1
    assert breaches[0]["late_by_min"] == 750