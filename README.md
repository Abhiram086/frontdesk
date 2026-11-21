# Frontdesk — Support Ticket System (Arvo Systems)

**Live URL:** `<YOUR-RENDER-URL>`
**Customer Portal:** `<YOUR-RENDER-URL>/portal`
**Repository:** `https://github.com/Abhiram086/frontdesk`

### Demo Accounts (Password for all: `Frontdesk@123`)
- **Manager (Meera):** `meera@arvo.test`
- **Support Agents (9 seeded):** `agent1@arvo.test` through `agent9@arvo.test`

---

## What It Is
Frontdesk replaces Arvo Systems' shared spreadsheet and WhatsApp workflow with a full-stack support ticket system featuring working-hours SLA tracking, atomic ticket claiming, strict internal-note isolation, and an append-only audit trail.

## Architecture
- **Backend:** Python 3.12 + FastAPI + `psycopg` 3 (plain SQL, no ORM, explicit row locks & triggers).
- **Database:** PostgreSQL 16 (`timestamptz` for all timestamps, `JSONB` for audit event payloads).
- **Frontend:** React 18 + Vite + `react-router-dom`, compiled into static assets and served directly by FastAPI (single URL, no CORS).
- **Background Sweeper:** Runs every 60 seconds inside FastAPI's lifespan task to auto-close silent/expired tickets and permanently record SLA breaches.

---

## How to Run Locally

### 1. Start PostgreSQL 16 (Docker)
```bash
docker run -d --name fd-db -p 5432:5432 -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=frontdesk postgres:16