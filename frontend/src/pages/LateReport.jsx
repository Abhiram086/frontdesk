import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { AppShell } from "../auth";
import Badge from "../components/Badge";
import { fmtMin, ist } from "../format";

const PRIORITY_TONE = { critical: "red", medium: "amber", low: "green" };

export default function LateReport() {
  const [rows, setRows] = useState([]);
  const [priority, setPriority] = useState("all");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api("/reports/late")
      .then(setRows)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = priority === "all" ? rows : rows.filter((r) => r.priority === priority);
  const byClock = {
    response: filtered.filter((r) => r.clock === "response").length,
    resolution: filtered.filter((r) => r.clock === "resolution").length,
  };

  return (
    <AppShell>
      <div className="space-between" style={{ marginBottom: 20 }}>
        <h1 className="page-title">Late Tickets Report</h1>
        <div className="row">
          <label style={{ margin: 0 }}>Priority:</label>
          <select
            style={{ width: "auto" }}
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
          >
            <option value="all">All</option>
            <option value="critical">Critical</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="grid-3" style={{ marginBottom: 20 }}>
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="muted">Total Breaches</div>
          <div style={{ fontSize: "1.8rem", fontWeight: 700, marginTop: 4 }}>{filtered.length}</div>
        </div>
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="muted">Response Breaches</div>
          <div style={{ fontSize: "1.8rem", fontWeight: 700, marginTop: 4 }}>{byClock.response}</div>
        </div>
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="muted">Resolution Breaches</div>
          <div style={{ fontSize: "1.8rem", fontWeight: 700, marginTop: 4 }}>{byClock.resolution}</div>
        </div>
      </div>

      {loading ? (
        <p className="muted">Loading report...</p>
      ) : filtered.length === 0 ? (
        <div className="card muted">No SLA breaches recorded yet.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Breached At (IST)</th>
                <th>Ticket</th>
                <th>Priority</th>
                <th>Clock</th>
                <th>Late By</th>
                <th>Assignee</th>
                <th>Reason</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => (
                <tr key={`${r.ticket_id}-${r.clock}-${i}`}>
                  <td style={{ whiteSpace: "nowrap" }}>{ist(r.at)}</td>
                  <td>
                    <Link to={`/tickets/${r.ticket_id}`} style={{ fontWeight: 500 }}>
                      #{r.ticket_id} {r.subject}
                    </Link>
                  </td>
                  <td><Badge text={r.priority} tone={PRIORITY_TONE[r.priority]} /></td>
                  <td style={{ textTransform: "capitalize" }}>{r.clock}</td>
                  <td><Badge text={fmtMin(-r.late_by_min)} tone="red" /></td>
                  <td>{r.assignee || "Unassigned"}</td>
                  <td>{r.reason}</td>
                  <td><Badge text={r.status.replace("_", " ")} tone="blue" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}