import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { TopBar } from "../auth";
import Badge from "../components/Badge";
import ClockChip from "../components/ClockChip";
import HistoryPanel from "../components/HistoryPanel";
import ReplyBox from "../components/ReplyBox";
import Thread from "../components/Thread";
import { fmtMin } from "../format";

const PRIORITY_TONE = { critical: "red", medium: "amber", low: "grey" };

export default function TicketDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    try {
      const res = await api(`/tickets/${id}`);
      setData(res);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    load();
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
      <>
        <TopBar />
        <main className="container">
          {error ? <div className="error">{error}</div> : <p className="muted">Loading ticket...</p>}
        </main>
      </>
    );
  }

  const { ticket, thread, clocks, is_assignee } = data;
  const canEdit = is_assignee && ticket.status !== "closed";
  const isOpen = ticket.status === "open" || ticket.status === "waiting_customer";

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
    <>
      <TopBar />
      <main className="container">
        <p style={{ marginTop: 0 }}>
          <Link to="/tickets">← Back to tickets</Link>
        </p>

        {error && <div className="error">{error}</div>}

        {/* Ownership banner (INC-0291) */}
        {!is_assignee && !ticket.assignee_id && ticket.status === "new" && (
          <div className="banner banner-info space-between">
            <span>This ticket is unassigned. Take it to reply or add notes.</span>
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

        {/* Ticket Header */}
        <section className="card">
          <div className="space-between">
            <div>
              <h2 style={{ margin: "0 0 6px" }}>
                #{ticket.id} — {ticket.subject}
              </h2>
              <div className="muted">
                Customer: <strong>{ticket.customer_name}</strong> ({ticket.customer_email}) · Assignee:{" "}
                <strong>{ticket.assignee || "Unassigned"}</strong>
                {ticket.follows_ticket_id && (
                  <>
                    {" "}· Follow-up to{" "}
                    <Link to={`/tickets/${ticket.follows_ticket_id}`}>
                      #{ticket.follows_ticket_id}
                    </Link>
                  </>
                )}
              </div>
            </div>

            <div className="row">
              <Badge text={ticket.status.replace("_", " ")} tone="blue" />
              {canEdit && isOpen ? (
                <select
                  aria-label="Priority"
                  style={{ width: "auto" }}
                  value={ticket.priority}
                  onChange={handlePriorityChange}
                >
                  <option value="critical">critical</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                </select>
              ) : (
                <Badge text={ticket.priority} tone={PRIORITY_TONE[ticket.priority]} />
              )}

              {canEdit && isOpen && (
                <button
                  className="btn btn-sm"
                  onClick={() => runAction(() => api(`/tickets/${id}/resolve`, { method: "POST" }))}
                >
                  Mark resolved
                </button>
              )}
              {canEdit && ticket.status === "resolved" && (
                <button
                  className="btn btn-sm"
                  onClick={() => runAction(() => api(`/tickets/${id}/reopen`, { method: "POST" }))}
                >
                  Reopen
                </button>
              )}
            </div>
          </div>
        </section>

        {/* SLA Clock Cards */}
        <div className="grid-2" style={{ marginBottom: 16 }}>
          {clocks.map((c) => (
            <div key={c.kind} className="card" style={{ marginBottom: 0 }}>
              <div className="space-between">
                <strong style={{ textTransform: "capitalize" }}>{c.kind} Clock</strong>
                <ClockChip clock={c} />
              </div>
              <div className="muted" style={{ marginTop: 6, fontSize: "0.85rem" }}>
                Target: {fmtMin(c.target_min).replace(" left", "")} · State: {c.state}
              </div>
            </div>
          ))}
        </div>

        {/* Conversation Thread + Composer */}
        <section className="card">
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
        </section>

        <HistoryPanel ticketId={id} refreshKey={refreshKey} />
      </main>
    </>
  );
}