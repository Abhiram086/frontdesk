import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { saveAuth } from "../auth";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      saveAuth(res.token, res.user);
      navigate("/tickets");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function fill(demoEmail) {
    setEmail(demoEmail);
    setPassword("Frontdesk@123");
  }

  return (
    <div className="login-split">
      <section className="login-brand">
        <span className="logo-mark logo-mark-lg">F</span>
        <h1>Frontdesk</h1>
        <p style={{ fontSize: "1.05rem", margin: "0 0 12px", fontWeight: 500 }}>
          Support. Resolve. Delight.
        </p>
        <p className="muted" style={{ maxWidth: 320, margin: 0 }}>
          Arvo Systems support ticket management with working-hours SLA tracking.
        </p>
      </section>

      <section className="login-panel">
        <div className="login-card">
          <h2 style={{ margin: "0 0 4px" }}>Sign In</h2>
          <p className="muted" style={{ margin: "0 0 22px" }}>
            Welcome back! Please sign in to continue.
          </p>

          {error && <div className="error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label>Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="agent1@arvo.test"
              />
            </div>
            <div className="field">
              <label>Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
            <button className="btn btn-primary btn-full" disabled={busy}>
              {busy ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <hr style={{ margin: "22px 0", border: "none", borderTop: "1px solid var(--border)" }} />

          <div className="muted" style={{ fontSize: "0.8rem" }}>
            <strong>Demo logins</strong> (password: <code>Frontdesk@123</code>)
            <div className="row" style={{ marginTop: 8, gap: 6 }}>
              <button type="button" className="btn btn-sm" onClick={() => fill("meera@arvo.test")}>
                Meera (Manager)
              </button>
              <button type="button" className="btn btn-sm" onClick={() => fill("agent1@arvo.test")}>
                Agent 1
              </button>
              <button type="button" className="btn btn-sm" onClick={() => fill("agent2@arvo.test")}>
                Agent 2
             </button>
            </div>
            <div style={{ marginTop: 8 }}>
              All 9 agents are added: <code>agent1@arvo.test</code> – <code>agent9@arvo.test</code> for test purposes
            </div>
          </div>
          <p style={{ marginTop: 18, marginBottom: 0, fontSize: "0.86rem" }}>
            Need to raise a ticket? <Link to="/portal" style={{ fontWeight: 600 }}>Open Customer Portal →</Link>
          </p>
        </div>
      </section>
    </div>
  );
}