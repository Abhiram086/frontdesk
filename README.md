# Frontdesk: Support Ticket System for Arvo Systems

Frontdesk replaces Arvo's shared spreadsheet and WhatsApp group with a real ticket system. It tracks **working-hours SLAs**, stops two agents taking the same ticket, keeps **private team notes away from customers**, and records an **append-only history** of everything that happens.

| | |
| :--- | :--- |
| **Live app** | `<YOUR-RENDER-URL>` |
| **Customer portal (simulator)** | `<YOUR-RENDER-URL>/portal` |
| **API docs (Swagger)** | `<YOUR-RENDER-URL>/docs` |
| **Repository** | https://github.com/Abhiram086/frontdesk |

> The app is on a free host and sleeps when idle. If the first load is slow, wait about a minute and refresh.

## Demo accounts

Password for every account: `Frontdesk@123`

| Role | Name | Email |
| :--- | :--- | :--- |
| Manager | Meera | `meera@arvo.test` |
| Agents (9 seeded) | Agent 1 to Agent 9 | `agent1@arvo.test` ... `agent9@arvo.test` |

## Try it in 5 minutes

1. Open `/portal`, raise a **critical** ticket ("I cannot work at all"), and copy the private link it shows.
2. Log in as `agent1`, open the **Unassigned** tab and click **Take**. Log in as `agent2` in another browser: the ticket is gone, and a direct claim returns `409`.
3. As `agent1`, send a **public reply**, then add an **internal note** containing the word `SECRET`.
4. Open the customer link: the reply is there and `SECRET` is nowhere on the page or in the network responses.
5. Use **Send and wait for customer**: the status becomes *waiting* and the clocks show *Paused*. Reply from the portal and they run again.
6. Mark the ticket **resolved**, then reopen it from the portal.
7. Log in as `meera` and open **Late report** and the ticket's **History** panel.

The seeded demo data already contains a late ticket, a waiting ticket, a resolved ticket and a ticket with an internal note.

---

## Architecture

| Layer | Choice |
| :--- | :--- |
| Backend | Python 3.12, FastAPI, Uvicorn, `psycopg` 3 with a connection pool. Plain SQL, no ORM, so locks, transactions and triggers stay visible. |
| Database | PostgreSQL 16. `timestamptz` everywhere, `JSONB` for audit payloads, triggers for append-only tables. |
| Auth | `bcrypt` password hashes, HS256 JWT (`PyJWT`), 12-hour expiry. |
| Frontend | React 18, Vite, `react-router-dom`, plain `fetch`, one CSS file. |
| Background job | A task started in FastAPI's lifespan runs every 60 seconds: auto-closes silent or expired tickets and permanently logs SLA breaches. It also runs once at startup, so it catches up after the host wakes. |
| Deployment | Multi-stage `Dockerfile`: Node builds React, Python serves it. One URL, no CORS setup. |

### Repository structure

```text
frontdesk/
├── Dockerfile                 # Multi-stage build (Node -> Python)
├── .dockerignore
├── .env.example               # Environment variable template
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── seed.py                # Idempotent seed data (Meera, 9 agents, holidays, demo tickets)
│   ├── migrations/
│   │   └── 001_init.sql       # Schema, indexes, append-only triggers
│   ├── app/
│   │   ├── main.py            # App, lifespan sweeper, static/SPA serving
│   │   ├── db.py              # Connection pool + tx() transaction helper
│   │   ├── auth.py            # Login, JWT verification, role guards
│   │   ├── sla.py             # Pure working-time engine (IST, weekends, holidays)
│   │   ├── clocks.py          # SLA clock transitions and breach recording
│   │   ├── events.py          # Audit log writer
│   │   ├── service.py         # Ticket workflows and sweep logic
│   │   ├── schemas.py         # Pydantic models (public leak guard)
│   │   ├── routes_staff.py    # Agent and manager endpoints
│   │   ├── routes_public.py   # Customer portal endpoints
│   │   └── migrate.py         # SQL migration runner
│   └── tests/
│       ├── conftest.py        # Isolated test DB and fixtures
│       ├── test_sla.py        # Working-time maths
│       ├── test_flow.py       # Priority change, auto-close, reopen, late report
│       └── test_security.py   # Double-claim race, note isolation, append-only triggers
└── frontend/
    ├── package.json
    ├── vite.config.js         # Dev proxy (/api -> http://localhost:8000)
    └── src/
        ├── App.jsx  api.js  auth.jsx  format.js  styles.css
        ├── components/        # Badge, ClockChip, Thread, ReplyBox, HistoryPanel
        └── pages/             # Login, Tickets, TicketDetail, LateReport, PortalNew, PortalTicket
```

---

## Run locally

**Prerequisites:** Python 3.12+, Node.js 20+ with npm, Docker (for PostgreSQL), Git.

### 1. Clone

```bash
git clone https://github.com/Abhiram086/frontdesk.git
cd frontdesk
cp .env.example .env
```

### 2. Start PostgreSQL 16

```bash
docker run -d --name fd-db -p 5432:5432 \
  -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=frontdesk postgres:16
```

On later days use `docker start fd-db` to keep your data.

### 3. Backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment and set the two variables for your shell:

**Linux / macOS (bash or zsh)**
```bash
source .venv/bin/activate
export DATABASE_URL="postgresql://postgres:pw@localhost:5432/frontdesk"
export JWT_SECRET="dev-secret-change-me"
```

**Linux (fish)**
```fish
source .venv/bin/activate.fish
set -gx DATABASE_URL "postgresql://postgres:pw@localhost:5432/frontdesk"
set -gx JWT_SECRET "dev-secret-change-me"
```

**Windows (PowerShell)**
```powershell
.venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql://postgres:pw@localhost:5432/frontdesk"
$env:JWT_SECRET="dev-secret-change-me"
```

Then install, migrate, seed and start:

```bash
pip install -r requirements.txt
python -m app.migrate
python seed.py
uvicorn app.main:app --reload --port 8000
```

Health check: <http://localhost:8000/api/health>. API docs: <http://localhost:8000/docs>.

### 4. Frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api/*` to `http://localhost:8000`.

### Run with Docker only (production-style)

```bash
docker build -t frontdesk .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://postgres:pw@host.docker.internal:5432/frontdesk" \
  -e JWT_SECRET="change-me" frontdesk
```

Open <http://localhost:8000>. The container applies migrations and seeds on start.

---

## Automated tests

With `fd-db` running and the virtual environment active:

```bash
cd backend
python -m pytest -v
```

Tests create and reset a separate `frontdesk_test` database, so your dev data is never touched. They cover:

- **Working-time maths:** Friday 6 PM to Sunday, holiday and weekend skipping, critical same-day deadline, pause and resume arithmetic.
- **Concurrency and permissions:** two simultaneous claims give `[200, 409]`; non-assignees get `403`.
- **Privacy:** private note text never appears in any public endpoint or in audit events.
- **Audit log:** `UPDATE`, `DELETE` and `TRUNCATE` on the append-only tables are rejected by PostgreSQL.
- **Lifecycle:** mid-ticket priority change, 5-working-day auto-close, reopen window with linked follow-up ticket, and the late report keeping breaches after resolution.

---

## Assumptions and decisions

The brief gave a story, not a requirements list. These are the choices made where it left gaps.

| Question | Decision | Why |
| :--- | :--- | :--- |
| Length of "half a day", "1 day", "3 days", "a week" | 1 working day = 9 hours = 540 min (09:30 to 18:30 IST). Half day = 270, 1 day = 540, 3 days = 1620, 1 week = 5 working days = 2700 min. | Simple arithmetic tied to the working day. |
| Critical: "fix the same working day" | Deadline is 18:30 of the working day on which the clock starts. A ticket raised after hours starts at 09:30 next working day and is due 18:30 that day. | Matches the sentence literally. |
| When a clock starts | At ticket creation. Outside working time, counting begins at the next opening. | A Friday 6 PM ticket is not late on Sunday. |
| Two clocks per ticket | Response clock stops at the first public agent reply. Resolution clock stops when the ticket is resolved. Internal notes never stop a clock. | Matches both of Meera's promises. |
| Pausing | Status `waiting_customer` pauses every unfinished clock. A customer reply resumes with the minutes that were left. | Customer waiting time is not Arvo's fault. |
| **Priority change mid-ticket** | **Keep the original start time and the working minutes already used, and apply the NEW priority's target to that used time.** Upgrading can make a ticket instantly late; downgrading gives time back. Paused clocks stay paused. Every change is logged. | Honest about how long the customer has waited, and stops "reset the timer" tricks. |
| Auto-close on customer silence | `waiting_customer` for 5 working days (2700 min) closes the ticket with reason `customer_silent`. | The one-working-week silence rule. |
| Reopen window | A resolved ticket can be reopened for 5 working days. After that the sweeper closes it (`reopen_window_over`). Closed is final. | The one-week reopen rule. |
| Customer writes after close | A new ticket is created, linked by `follows_ticket_id`, with fresh clocks. | "After that it is a new ticket." |
| Reopen effect on timers | Resolution clock restarts from zero with the current priority's target. Response clock stays stopped. | A reopen is a fresh fix attempt; the first reply was already given. |
| Who can act | Any staff member can read any ticket. Only the assigned agent can reply, note, resolve, reopen or change priority. Managers can view all queues and the Late report. | Closes the INC-0291 duplicate-reply risk. |
| Claiming | One atomic `UPDATE ... WHERE assignee_id IS NULL`. The second agent gets `409`. | The database decides the winner, not the UI. |
| "Late": stored or computed? | Remaining minutes are computed live on every read. Breaches are also written once as permanent `sla_breached` events with a reason. | Screens are always right, and history survives resolution. |
| Festival holidays | Editable `holidays` table seeded with sample dates (Christmas, New Year, Republic Day). | No official list was provided. |
| Time zone | SLA logic runs in `Asia/Kolkata`. All timestamps are stored as `timestamptz`. | Matches the Kochi office. |

---

## How each incident is prevented

**INC-0291: two agents took and answered the same ticket**
- Claiming is a single atomic `UPDATE ... WHERE assignee_id IS NULL AND status = 'new'`. A concurrent second claim gets `409 Conflict`.
- Every mutating endpoint checks `require_assignee()` on the server. A non-assignee trying to reply, note, resolve, reopen or change priority gets `403`.

**INC-0304: a private note reached a customer**
- Notes live in `internal_notes`, a separate table from `messages`, and no `/api/public/*` route queries it.
- Public endpoints return a strict Pydantic `PublicTicket` model, so undeclared fields are dropped.
- Audit events store only the `note_id`, never the note text.

**INC-0318: nobody could prove what happened and when**
- `BEFORE UPDATE OR DELETE` and `BEFORE TRUNCATE` triggers on `events`, `messages` and `internal_notes` reject any change.
- All timestamps are created by the server, never sent by the client.
- Every action (created, claimed, reply, note, status, priority, breach, close) writes an event with actor and time.

---

## API overview

Full interactive docs are at `/docs`.

| Method and path | Access | Purpose |
| :--- | :--- | :--- |
| `POST /api/auth/login` | Public | Log in; returns JWT and user |
| `GET /api/health` | Public | Health check |
| `GET /api/tickets?view=mine\|unassigned\|all` | Staff (`all`: manager) | Queue with live SLA clocks, late first |
| `GET /api/tickets/{id}` | Staff | Ticket, merged thread (messages and notes), clocks |
| `POST /api/tickets/{id}/claim` | Agent | Atomic claim (`409` if taken) |
| `POST /api/tickets/{id}/reply` | Assignee | Public reply; can pause for customer |
| `POST /api/tickets/{id}/notes` | Assignee | Team-only note |
| `POST /api/tickets/{id}/resolve` | Assignee | Stop clocks, mark resolved |
| `POST /api/tickets/{id}/reopen` | Assignee | Reopen within 5 working days |
| `POST /api/tickets/{id}/priority` | Assignee | Change priority mid-ticket |
| `GET /api/tickets/{id}/events` | Staff | Full audit trail |
| `GET /api/reports/late` | Manager | Historical SLA breaches with reasons |
| `POST /api/public/tickets` | Customer | Raise a ticket; returns private token |
| `GET /api/public/tickets/{token}` | Customer | Public thread only |
| `POST /api/public/tickets/{token}/reply` | Customer | Reply; resumes clocks, reopens, or starts a linked follow-up |
| `POST /api/public/tickets/{token}/reopen` | Customer | Reopen inside the window |

---

## What was not finished, and why

1. **No email in or out.** Customers use the web portal with a private link. Email needs a mail service and more than two extra hours.
2. **No reassign or release.** Once claimed, moving a ticket needs a database change.
3. **No hash chain on the audit log.** Triggers block every application-level edit, but a database superuser could drop them.
4. **No admin screens for holidays or staff.** Both are managed in PostgreSQL (`holidays`, `users`). The holiday list is sample data.
5. **No password reset, pagination or file attachments.** The time went into the SLA engine, concurrency safety and data isolation.
6. **No date filter or CSV export on the Late report.** It shows breach causes and a priority filter only.
7. **No automated frontend tests.** Automated coverage targets the time engine, the claim race, note isolation, the audit triggers and the ticket lifecycle.