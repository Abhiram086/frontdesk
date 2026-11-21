import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import Badge from "../components/Badge";
import { ist } from "../format";

const FRIENDLY_STATUS = {
  new: "Received — waiting for an agent",
  open: "In progress",
  waiting_customer: "Waiting for your reply",
  resolved: "Marked as resolved",
  closed: "Closed",
};

export default function PortalTicket() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [body, setBody] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setTicket(await api(`/public/tickets/${token}`));
    } catch (err) {
      setError(err.message);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  async function sendReply(e) {
    e.preventDefault();
    if (!body.trim()) return;
    setError("");
    setBusy(true);
    try {
      const res = await api(`/public/tickets/${token}/reply`, {
        method: "POST",
        body: { body: body.trim() },
      });
      setBody("");
      if (res.token && res.token !== token) {
        navigate(`/portal/t/${res.token}`);
      } else {
        await load();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleReopen() {
    setError("");
    setBusy(true);
    try {
      await api(`/public/tickets/${token}/reopen`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container narrow">
      <div className="banner banner-warn space-between">
        <span>Customer simulator: public customer view</span>
        <Link to="/portal">New ticket</Link>
      </div>

      {error && <div className="error">{error}</div>}

      {!ticket ? (
        <p className="muted">Loading ticket...</p>
      ) : (
        <div className="card">
          <div className="space-between" style={{ marginBottom: 16 }}>
            <div>
              <h2 style={{ margin: "0 0 4px" }}>{ticket.subject}</h2>
              <div className="muted">Created {ist(ticket.created_at)}</div>
            </div>
            <Badge text={FRIENDLY_STATUS[ticket.status] || ticket.status} tone="blue" />
          </div>

          <div className="thread">
            {ticket.messages.map((m, i) => (
              <div
                key={i}
                className={`bubble ${m.author === "you" ? "bubble-agent" : "bubble-customer"}`}
              >
                <div className="bubble-meta">
                  <strong>{m.author === "you" ? "You" : "Arvo Support"}</strong>
                  <span>{ist(m.at)}</span>
                </div>
                <div>{m.body}</div>
              </div>
            ))}
          </div>

          {ticket.can_reopen && (
            <div className="banner banner-info space-between">
              <span>This ticket was marked resolved. Still having trouble?</span>
              <button className="btn btn-sm btn-primary" disabled={busy} onClick={handleReopen}>
                Not happy? Reopen
              </button>
            </div>
          )}

          {ticket.status === "closed" && (
            <div className="banner banner-warn">
              This ticket is closed. Sending a message below will automatically open a linked follow-up ticket.
            </div>
          )}

          <form onSubmit={sendReply}>
            <div className="field">
              <label>Reply</label>
              <textarea
                rows={3}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Write a message to Arvo Support..."
              />
            </div>
            <button className="btn btn-primary" disabled={busy || !body.trim()}>
              {busy ? "Sending..." : "Send message"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}