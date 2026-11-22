# Frontdesk

A support ticket system for the fictional company Arvo Systems, built for the iNav Technologies Full Stack Developer hiring test. It replaces a shared spreadsheet and a WhatsApp group with one system that tracks deadlines in **working hours**, prevents two agents taking the same ticket, keeps **private team notes away from customers**, and keeps a **tamper-proof history** of everything that happens.

## Live links

| | |
| :--- | :--- |
| **App (agent login)** | https://frontdesk-4ya9.onrender.com/ |
| **Customer portal** | https://frontdesk-4ya9.onrender.com/portal |
| **API docs (Swagger)** | https://frontdesk-4ya9.onrender.com/docs |
| **Source code** | https://github.com/Abhiram086/frontdesk |

> Hosted on a free tier, so the first load after a quiet period can take up to a minute.

**Demo accounts** (password for all: `Frontdesk@123`)

| Role | Email |
| :--- | :--- |
| Manager | `meera@arvo.test` |
| Agents | `agent1@arvo.test` to `agent9@arvo.test` |

## Quick tour (5 minutes)

1. Open `/portal` and raise a **critical** ticket. Copy the private link it gives you.
2. Log in as `agent1`, open **Unassigned**, click **Take**. A second agent cannot take the same ticket.
3. Send a public reply, then add an **internal note**. Open the customer link: the reply is there, the note never is.
4. Use **Send and wait for customer**. The SLA clocks pause. Reply from the portal and they resume.
5. Mark the ticket resolved, then reopen it from the portal.
6. Log in as `meera` to see the **Late report** and each ticket's **History**.

## How it works

**Tickets and SLAs.** Each ticket has two clocks: *first response* and *resolution*. Targets depend on priority and are counted in **working time only** (09:30 to 18:30 IST, Monday to Friday, minus holidays).

| Priority | Reply within | Fix within |
| :--- | :--- | :--- |
| Critical | 2 working hours | End of the same working day |
| Medium | Half a working day | 3 working days |
| Low | 1 working day | 5 working days |

**Lifecycle:** `new` -> `open` -> `waiting_customer` -> `resolved` -> `closed`

- Clocks **pause** while waiting for the customer and resume on their reply.
- No customer reply for 5 working days: the ticket **auto-closes**.
- A resolved ticket can be **reopened** for 5 working days. After that, a customer message starts a new, linked ticket.
- Changing priority mid-ticket keeps the time already used and applies the new target to it.
- A background job runs every minute to auto-close tickets and permanently record late tickets with a reason.

**The three incidents from the brief, and the fix for each**

| Incident | What prevents it |
| :--- | :--- |
| Two agents took the same ticket | Claiming is one atomic database update, so the second agent gets `409`. Only the assigned agent can reply, note, resolve or reopen. |
| A private note reached a customer | Notes live in their own table. Customer endpoints only read the public messages table and return a fixed, whitelisted response. |
| Nobody could prove what happened | Every action is written to an append-only event log with actor and server-set time. Database triggers block any update or delete. |

## Architecture

```text
 Browser (React app)
        |
        |  HTTPS   /api/*   JSON + JWT
        v
 FastAPI (Python)  -- also serves the built React files
   |-- auth        login, roles (agent / manager)
   |-- staff API   tickets, claim, reply, notes, resolve, reopen, priority, reports
   |-- public API  customer portal, secret-token links, no login
   |-- SLA engine  working-time maths (IST, weekends, holidays)
   |-- sweeper     runs every 60 s: auto-close, record late tickets
        |
        v
 PostgreSQL  tickets | messages | internal_notes | sla_clocks | events | holidays | users
```

| Layer | Technology |
| :--- | :--- |
| Backend | Python 3.12, FastAPI, psycopg 3 (plain SQL, no ORM) |
| Database | PostgreSQL 16 (Neon in production) |
| Frontend | React 19, Vite, React Router |
| Auth | bcrypt password hashes, JWT |
| Hosting | One Docker image on Render: Node builds the frontend, Python serves everything |

Project layout: `backend/app` (API and logic), `backend/migrations` (schema), `backend/tests`, `frontend/src` (pages and components), `Dockerfile` at the root.

## Pages

| Page | URL | Who | What it does |
| :--- | :--- | :--- | :--- |
| Login | `/login` | Staff | Sign in |
| Tickets | `/tickets` | Staff | Queue with **Late** and **Waiting** badges, live countdowns, Unassigned tab with a Take button |
| Ticket detail | `/tickets/:id` | Staff | Conversation, reply or team-only note, clocks, priority, resolve and reopen, full history |
| Late report | `/manager/late` | Manager | Every late ticket, which clock, how late, and why |
| Raise a ticket | `/portal` | Customer | Simple form with plain-language severity choices |
| Customer ticket | `/portal/t/:token` | Customer | Public conversation only, reply, reopen |

## Main API endpoints

Full interactive docs are at `/docs`.

| Endpoint | Who | Purpose |
| :--- | :--- | :--- |
| `POST /api/auth/login` | Anyone | Get a token |
| `GET /api/tickets?view=mine\|unassigned\|all` | Staff | Ticket queue with SLA status |
| `GET /api/tickets/{id}` | Staff | Ticket, thread (including notes), clocks |
| `POST /api/tickets/{id}/claim` | Agent | Take a ticket (`409` if taken) |
| `POST /api/tickets/{id}/reply` | Assignee | Public reply |
| `POST /api/tickets/{id}/notes` | Assignee | Team-only note |
| `POST /api/tickets/{id}/resolve` `/reopen` `/priority` | Assignee | Change ticket state |
| `GET /api/tickets/{id}/events` | Staff | Audit history |
| `GET /api/reports/late` | Manager | Late tickets with reasons |
| `POST /api/public/tickets` | Customer | Raise a ticket, returns private token |
| `GET /api/public/tickets/{token}` | Customer | View public conversation |
| `POST /api/public/tickets/{token}/reply` `/reopen` | Customer | Reply or reopen |
| `GET /api/health` | Anyone | Health check |

## Key decisions

Where the brief left gaps, these are the choices made:

- **A working day is 9 hours (540 minutes).** "Half a day" is 270 minutes, "a week" is 5 working days.
- **Priority change keeps the time already used** and applies the new target to it. Upgrading can make a ticket late immediately; the change is logged.
- **Reopen restarts only the resolution clock.** The first reply was already given.
- **Late is calculated live on every screen**, and each breach is also stored permanently so reports survive resolution.
- **Holidays are sample data** in an editable table, since no official list was given.

## What is not included

Email in and out, ticket reassignment, admin screens for staff and holidays, password reset, pagination, file attachments, CSV export, and frontend automated tests. The time went into the SLA engine, concurrency safety and data isolation. A hash chain on the audit log would also make tampering detectable by a database administrator; today, triggers block all changes made through the application.

---

## Optional: run it locally

You need **Python 3.12+**, **Node.js 20+**, **Git** and **Docker** (used only to run PostgreSQL).

### 1. Get the code and start PostgreSQL (same on Linux and Windows)

```bash
git clone https://github.com/Abhiram086/frontdesk.git
cd frontdesk
docker run -d --name fd-db -p 5432:5432 -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=frontdesk postgres:16
```

On later days, just run `docker start fd-db`.

### 2. Backend

**Linux / macOS**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://postgres:pw@localhost:5432/frontdesk"
export JWT_SECRET="dev-secret-change-me"
python -m app.migrate
python seed.py
uvicorn app.main:app --reload --port 8000
```

**Windows (PowerShell)**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "postgresql://postgres:pw@localhost:5432/frontdesk"
$env:JWT_SECRET = "dev-secret-change-me"
python -m app.migrate
python seed.py
uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks the activate script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

The API is now at http://localhost:8000 (docs at `/docs`).

### 3. Frontend (second terminal, same on both systems)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. It forwards `/api` calls to the backend on port 8000.

### 4. Tests (optional)

With the backend environment active and the database running:

```bash
cd backend
python -m pytest -v
```

The tests use a separate `frontdesk_test` database, so your demo data is not touched.
