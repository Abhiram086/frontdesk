import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { getUser, TopBar } from "../auth";
import Badge from "../components/Badge";
import ClockChip from "../components/ClockChip";

const PRIORITY_TONE = { critical: "red", medium: "amber", low: "grey" };

export default function Tickets() {
  const user = getUser();
  const navigate = useNavigate();
  const [view, setView] = useState("mine");
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await api(`/tickets?view=${view}`);
      setRows(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [view]);

  useEffect(() => {
    setLoading(true);
    setError("");
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load]);

  async function takeTicket(e, tid) {
    e.stopPropagation(); // Keep row click from firing at the same time
    setError("");
    try {
      await api(`/tickets/${tid}/claim`, { method: "POST" });
      navigate(`/tickets/${tid}`);
    } catch (err) {
      setError(err.message || "Someone else just took this ticket");
      load();
    }
  }

  return (
    <>
      <TopBar />
      <main className="container">
        <div className="space-between" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Support Queue</h2>
          <button className="btn btn-sm" onClick={load}>Refresh</button>
        </div>

        <div className="tabs">
          <button
            className={`tab ${view === "mine" ? "active" : ""}`}
            onClick={() => setView("mine")}
          >
            My tickets
          </button>
          <button
            className={`tab ${view === "unassigned" ? "active" : ""}`}
            onClick={() => setView("unassigned")}
          >
            Unassigned
          </button>
          {user?.role === "manager" && (
            <button
              className={`tab ${view === "all" ? "active" : ""}`}
              onClick={() => setView("all")}
            >
              All tickets
            </button>
          )}
        </div>

        {error && <div className="error">{error}</div>}

        {loading ? (
          <p className="muted">Loading tickets...</p>
        ) : rows.length === 0 ? (
          <div className="card muted">No tickets in this queue right now.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Subject</th>
                <th>Customer</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Assignee</th>
                <th>Response</th>
                <th>Resolution</th>
                {view === "unassigned" && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const resp = r.clocks.find((c) => c.kind === "response");
                const res = r.clocks.find((c) => c.kind === "resolution");
                return (
                  <tr
                    key={r.id}
                    className={`clickable ${r.late ? "row-late" : ""}`}
                    onClick={() => navigate(`/tickets/${r.id}`)}
                  >
                    <td>#{r.id}</td>
                    <td>
                      <div style={{ fontWeight: 500 }}>{r.subject}</div>
                      <div className="row" style={{ marginTop: 4, gap: 6 }}>
                        {r.late && <Badge text="LATE" tone="red" />}
                        {r.waiting && <Badge text="WAITING ON CUSTOMER" tone="amber" />}
                      </div>
                    </td>
                    <td>{r.customer_name}</td>
                    <td><Badge text={r.priority} tone={PRIORITY_TONE[r.priority]} /></td>
                    <td><Badge text={r.status.replace("_", " ")} tone="blue" /></td>
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
        )}
      </main>
    </>
  );
}
