import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { AppShell } from "../auth";
import Badge from "../components/Badge";
import ClockChip from "../components/ClockChip";
import HistoryPanel from "../components/HistoryPanel";
import ReplyBox from "../components/ReplyBox";
import Thread from "../components/Thread";
import { ist } from "../format";

const PRIORITY_TONE = { critical: "red", medium: "amber", low: "green" };
const STATUS_TONE = {
  new: "grey",
  open: "blue",
  waiting_customer: "purple",
  resolved: "green",
  closed: "grey",
};

export default function TicketDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState("conversation");
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    try {
      setData(await api(`/tickets/${id}`));
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    load();
    const id = setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, 5000);
    return () => clearInterval(id);
  }, [load]);

  async function runAction(fn) {
    setError("");
    try {
      await fn();
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!data) {
    return (
      <AppShell>
        {error ? <div className="error">{error}</div> : <p className="muted">Loading ticket...</p>}
      </AppShell>
    );
  }

  const { ticket, thread, clocks, is_assignee } = data;
  const canEdit = is_assignee && ticket.status !== "closed";
  const isOpen = ticket.status === "open" || ticket.status === "waiting_customer";
  const respClock = clocks.find((c) => c.kind === "response");
  const resClock = clocks.find((c) => c.kind === "resolution");

  async function handlePriorityChange(e) {
    const next = e.target.value;
    if (next === ticket.priority) return;
    const ok = window.confirm(
      "Timer keeps the time already used and applies the new target. Change priority?"
    );
    if (!ok) return;
    await runAction(() =>
      api(`/tickets/${id}/priority`, { method: "POST", body: { priority: next } })
    );
  }

  return (
    <AppShell>
      {/* Top breadcrumb + ticket number */}
      <div className="space-between" style={{ marginBottom: 14 }}>
        <Link to="/tickets" className="muted">← Back to Tickets</Link>
        <div className="row">
          <span style={{ fontWeight: 700 }}>#{ticket.id}</span>
          <Badge text={ticket.status.replace("_", " ")} tone={STATUS_TONE[ticket.status] || "grey"} />
        </div>
      </div>

      <h1 className="page-title" style={{ marginBottom: 16 }}>{ticket.subject}</h1>

      {error && <div className="error">{error}</div>}

      {/* Ownership banners (INC-0291) */}
      {!is_assignee && !ticket.assignee_id && ticket.status === "new" && (
        <div className="banner banner-info space-between">
          <span>This ticket is unassigned. Claim it to reply or add internal notes.</span>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => runAction(() => api(`/tickets/${id}/claim`, { method: "POST" }))}
          >
            Take this ticket
          </button>
        </div>
      )}
      {!is_assignee && ticket.assignee_id && (
        <div className="banner banner-warn">
          Read-only: assigned to <strong>{ticket.assignee}</strong>. Only the assignee can reply or update this ticket.
        </div>
      )}

      {/* 4-column metadata strip */}
      <div className="meta-strip">
        <div>
          <div className="meta-label">Priority</div>
          <Badge text={ticket.priority} tone={PRIORITY_TONE[ticket.priority]} />
        </div>
        <div>
          <div className="meta-label">Created</div>
          <div className="meta-value">{ist(ticket.created_at)}</div>
        </div>
        <div>
          <div className="meta-label">Response SLA</div>
          <ClockChip clock={respClock} />
        </div>
        <div>
          <div className="meta-label">Resolution SLA</div>
          <ClockChip clock={resClock} />
        </div>
      </div>

      {/* Main 2-column workspace */}
      <div className="detail-grid">
        <section className="card">
          <div className="tabs">
            <button
              className={`tab ${activeTab === "conversation" ? "active" : ""}`}
              onClick={() => setActiveTab("conversation")}
            >
              Conversation
            </button>
            <button
              className={`tab ${activeTab === "history" ? "active" : ""}`}
              onClick={() => setActiveTab("history")}
            >
              Audit History
            </button>
          </div>

          {activeTab === "conversation" ? (
            <>
              <Thread items={thread} />
              <ReplyBox
                disabled={!canEdit || !isOpen}
                onSendReply={(body, wait) =>
                  runAction(() =>
                    api(`/tickets/${id}/reply`, {
                      method: "POST",
                      body: { body, wait_for_customer: wait },
                    })
                  )
                }
                onSendNote={(body) =>
                  runAction(() =>
                    api(`/tickets/${id}/notes`, { method: "POST", body: { body } })
                  )
                }
              />
            </>
          ) : (
            <HistoryPanel ticketId={id} refreshKey={refreshKey} />
          )}
        </section>

        <aside className="card detail-side">
          <h3 style={{ margin: "0 0 14px", fontSize: "0.95rem" }}>Ticket Details</h3>

          <div className="side-field">
            <div className="meta-label">Customer</div>
            <div className="meta-value">{ticket.customer_name}</div>
            <div className="muted" style={{ fontSize: "0.82rem" }}>{ticket.customer_email}</div>
          </div>

          <div className="side-field">
            <div className="meta-label">Assigned To</div>
            <div className="meta-value">{ticket.assignee || "Unassigned"}</div>
          </div>

          {ticket.follows_ticket_id && (
            <div className="side-field">
              <div className="meta-label">Follow-up To</div>
              <Link to={`/tickets/${ticket.follows_ticket_id}`} style={{ fontWeight: 600 }}>
                Ticket #{ticket.follows_ticket_id}
              </Link>
            </div>
          )}

          {canEdit && isOpen && (
            <div className="side-field">
              <label>Change Priority</label>
              <select value={ticket.priority} onChange={handlePriorityChange}>
                <option value="critical">Critical</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          )}

          {(canEdit && (isOpen || ticket.status === "resolved")) && (
            <>
              <hr style={{ margin: "16px 0", border: "none", borderTop: "1px solid var(--border)" }} />
              <h3 style={{ margin: "0 0 10px", fontSize: "0.95rem" }}>Actions</h3>
              {isOpen && (
                <button
                  className="btn btn-primary btn-full"
                  onClick={() => runAction(() => api(`/tickets/${id}/resolve`, { method: "POST" }))}
                >
                  Mark Resolved
                </button>
              )}
              {ticket.status === "resolved" && (
                <button
                  className="btn btn-full"
                  onClick={() => runAction(() => api(`/tickets/${id}/reopen`, { method: "POST" }))}
                >
                  Reopen Ticket
                </button>
              )}
            </>
          )}
        </aside>
      </div>
    </AppShell>
  );
}