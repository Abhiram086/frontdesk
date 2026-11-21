from datetime import datetime, timedelta, timezone
import bcrypt

from app import service as sv
from app.db import tx


def main():
    with tx() as cur:
        cur.execute("SELECT count(*) AS n FROM users")
        if cur.fetchone()["n"] > 0:
            return  # Already seeded

        pw = bcrypt.hashpw(b"Frontdesk@123", bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING *",
            ("Meera", "meera@arvo.test", pw, "manager"),
        )

        agents = []
        for i in range(1, 10):
            cur.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING *",
                (f"Agent {i}", f"agent{i}@arvo.test", pw, "agent"),
            )
            agents.append(cur.fetchone())

        cur.execute(
            """
            INSERT INTO holidays (day, name) VALUES
                ('2026-12-25', 'Christmas'),
                ('2027-01-01', 'New Year'),
                ('2027-01-26', 'Republic Day')
            """
        )

        now = datetime.now(timezone.utc)
        a1, a2, a3 = agents[0], agents[1], agents[2]

        # 1 & 2. Two unassigned new tickets (one critical, one low)
        sv.create_ticket(
            cur, "Nikhil Verma", "nikhil@acme.in",
            "Checkout API returning 500 for all users",
            "Our payment webhook started failing 20 minutes ago. Nobody can check out.",
            "critical", now=now - timedelta(minutes=25),
        )
        sv.create_ticket(
            cur, "Sneha Nair", "sneha@keralatech.in",
            "How do I add a second billing email?",
            "We want invoices sent to accounts@ as well as my email.",
            "low", now=now - timedelta(hours=2),
        )

        # 3. Claimed critical ticket already late (created 4 days ago, no reply)
        t_late = sv.create_ticket(
            cur, "Arjun Menon", "arjun@finserve.in",
            "Production login broken after SSO update",
            "All 40 staff members are locked out of the dashboard.",
            "critical", now=now - timedelta(days=4),
        )
        sv.claim_ticket(cur, t_late["id"], a1, now=now - timedelta(days=4) + timedelta(minutes=15))

        # 4. Medium ticket waiting on customer (shows paused SLA clock)
        t_wait = sv.create_ticket(
            cur, "Priya Pillai", "priya@brightedu.in",
            "CSV export missing phone number column",
            "When I export contacts, column D is blank.",
            "medium", now=now - timedelta(days=1),
        )
        sv.claim_ticket(cur, t_wait["id"], a1, now=now - timedelta(hours=22))
        sv.agent_reply(
            cur, t_wait["id"], a1,
            "Could you share which browser and filter settings you used?",
            wait_for_customer=True, now=now - timedelta(hours=20),
        )

        # 5. Ticket with an internal note (shows yellow team-only note & proves portal hides it)
        t_note = sv.create_ticket(
            cur, "Rohan Kapoor", "rohan@metrologistics.in",
            "Duplicate invoice charged twice",
            "We were billed twice for November. Please refund immediately.",
            "medium", now=now - timedelta(hours=6),
        )
        sv.claim_ticket(cur, t_note["id"], a1, now=now - timedelta(hours=5))
        sv.agent_reply(
            cur, t_note["id"], a1,
            "Hi Rohan, I am checking with our billing team right now and will update you shortly.",
            wait_for_customer=False, now=now - timedelta(hours=4),
        )
        sv.add_note(
            cur, t_note["id"], a1,
            "Checked Stripe logs: duplicate charge confirmed. Escalated to finance for reversal—do not promise exact refund date yet.",
            now=now - timedelta(hours=3, minutes=50),
        )

        # 6. Resolved ticket inside the 5-working-day reopen window
        t_res = sv.create_ticket(
            cur, "Divya Krishnan", "divya@greenleaf.in",
            "Unable to reset 2FA authenticator",
            "Got a new phone and lost my authenticator codes.",
            "medium", now=now - timedelta(days=2),
        )
        sv.claim_ticket(cur, t_res["id"], a2, now=now - timedelta(days=2) + timedelta(minutes=30))
        sv.agent_reply(
            cur, t_res["id"], a2,
            "I have reset your 2FA. You can enroll your new phone on next login.",
            wait_for_customer=False, now=now - timedelta(days=2) + timedelta(hours=1),
        )
        sv.resolve_ticket(cur, t_res["id"], a2, now=now - timedelta(days=1))

        # 7. Active low-priority ticket assigned to Agent 3
        t_low = sv.create_ticket(
            cur, "Vikram Joshi", "vikram@solaris.in",
            "Request for dark mode in reports",
            "Would be great to have a dark theme option on the analytics page.",
            "low", now=now - timedelta(hours=3),
        )
        sv.claim_ticket(cur, t_low["id"], a3, now=now - timedelta(hours=2))

    # Run one sweep so any already-late seeded tickets appear in the Late Report immediately
    sv.run_sweep()
    print("Seed data inserted.")


if __name__ == "__main__":
    main()