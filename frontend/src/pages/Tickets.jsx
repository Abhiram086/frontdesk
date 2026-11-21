import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { AppShell } from "../auth";
import Badge from "../components/Badge";
import ClockChip from "../components/ClockChip";

const PRIORITY_TONE = { critical: "red", medium: "amber", low: "green" };
const STATUS_TONE = {
  new: "grey",
  open: "blue",
  waiting_customer: "purple",
  resolved: "green",
  closed: "grey",
};
const TITLES = { mine: "My Tickets", unassigned: "Unassigned Queue", all: "All Tickets" };

export default function Tickets() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const view = params.get("view") || "mine";

  const [rows, setRows] = useState([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setRows(await api(`/tickets?view=${view}`));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [view]);

  useEffect(() => {
    setLoading(true);
    setStatusFilter("all");
    setError("");
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load]);

  async function takeTicket(e, tid) {
    e.stopPropagation();
    setError("");
    try {
      await api(`/tickets/${tid}/claim`, { method: "POST" });
      navigate(`/tickets/${tid}`);
    } catch (err) {
      setError(err.message || "Someone else just took this ticket");
      load();
    }
  }

  // Pure client-side filtering on the current queue
  const filtered = rows.filter((r) => {
    if (statusFilter !== "all" && r.status !== statusFilter) return false;
    if (query.trim()) {
      const q = query.toLowerCase();
      return (
        String(r.id).includes(q) ||
        r.subject.toLowerCase().includes(q) ||
        r.customer_name.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const count = (s) => rows.filter((r) => r.status === s).length;

  return (
    <AppShell>
      <div className="space-between" style={{ marginBottom: 20 }}>
        <h1 className="page-title">{TITLES[view] || "Tickets"}</h1>
        <div className="row">
          <input
            className="search-input"
            placeholder="Search tickets... (e.g. #4 or subject)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="btn btn-sm" onClick={load}>Refresh</button>
        </div>
      </div>

      {view !== "unassigned" && (
        <div className="pill-row">
          {[
            ["all", `All (${rows.length})`],
            ["open", `Open (${count("open")})`],
            ["waiting_customer", `Waiting Customer (${count("waiting_customer")})`],
            ["resolved", `Resolved (${count("resolved")})`],
          ].map(([key, label]) => (
            <button
              key={key}
              className={`pill ${statusFilter === key ? "active" : ""}`}
              onClick={() => setStatusFilter(key)}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {loading ? (
        <p className="muted">Loading tickets...</p>
      ) : filtered.length === 0 ? (
        <div className="card muted">No matching tickets in this queue.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Subject</th>
                <th>Customer</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Assignee</th>
                <th>Response SLA</th>
                <th>Resolution SLA</th>
                {view === "unassigned" && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => {
                const resp = r.clocks.find((c) => c.kind === "response");
                const res = r.clocks.find((c) => c.kind === "resolution");
                return (
                  <tr
                    key={r.id}
                    className={`clickable ${r.late ? "row-late" : ""}`}
                    onClick={() => navigate(`/tickets/${r.id}`)}
                  >
                    <td style={{ color: "var(--muted)", fontWeight: 500 }}>#{r.id}</td>
                    <td>
                      <div style={{ fontWeight: 500 }}>{r.subject}</div>
                      {r.late && (
                        <div style={{ marginTop: 4 }}>
                          <Badge text="LATE" tone="red" />
                        </div>
                      )}
                    </td>
                    <td>{r.customer_name}</td>
                    <td><Badge text={r.priority} tone={PRIORITY_TONE[r.priority]} /></td>
                    <td>
                      <Badge
                        text={r.status.replace("_", " ")}
                        tone={STATUS_TONE[r.status] || "grey"}
                      />
                    </td>
                    <td>{r.assignee || <span className="muted">Unassigned</span>}</td>
                    <td><ClockChip clock={resp} /></td>
                    <td><ClockChip clock={res} /></td>
                    {view === "unassigned" && (
                      <td>
                        <button
                          className="btn btn-sm btn-primary"
                          onClick={(e) => takeTicket(e, r.id)}
                        >
                          Take
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}