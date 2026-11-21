import { useState } from "react";
import { api } from "../api";
import { ist } from "../format";

function describeEvent(e) {
  const p = e.payload || {};
  switch (e.type) {
    case "ticket_created":
      return `Ticket created (${p.priority})${p.follows ? ` — follow-up to #${p.follows}` : ""}`;
    case "claimed":
      return `Claimed by ${p.agent}`;
    case "agent_reply":
      return `Agent sent a public reply (message #${p.message_id})`;
    case "customer_reply":
      return "Customer replied";
    case "note_added":
      return `Internal note added (note #${p.note_id})`;
    case "status_changed":
      return `Status changed to ${p.to}`;
    case "priority_changed":
      return `Priority changed from ${p.from} to ${p.to}`;
    case "resolved":
      return "Marked as resolved";
    case "reopened":
      return "Ticket reopened";
    case "closed":
      return `Closed automatically (${p.reason})`;
    case "sla_breached":
      return `SLA breached (${p.kind}, late by ${p.late_by_min}m): ${p.reason}`;
    default:
      return e.type;
  }
}

export default function HistoryPanel({ ticketId, refreshKey }) {
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) {
      setLoading(true);
      try {
        setEvents(await api(`/tickets/${ticketId}/events`));
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <section className="card history-panel">
      <button type="button" className="btn btn-sm" onClick={toggle}>
        {open ? "Hide" : "Show"} Audit History
      </button>

      {open && (
        <div className="history-list" data-refresh={refreshKey}>
          {loading ? (
            <p className="muted">Loading history...</p>
          ) : (
            <ul>
              {events.map((e) => (
                <li key={e.id}>
                  <span className="history-time">{ist(e.at)}</span>
                  <span className="history-actor">{e.actor}</span>
                  <span>{describeEvent(e)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}