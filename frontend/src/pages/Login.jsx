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
    <div className="container narrow" style={{ marginTop: 64 }}>
      <div className="card">
        <h1 style={{ marginTop: 0 }}>Frontdesk Sign In</h1>
        <p className="muted">Arvo Systems support workspace</p>

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
            />
          </div>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <hr style={{ margin: "20px 0", border: "none", borderTop: "1px solid var(--border)" }} />

        <div className="muted" style={{ fontSize: "0.85rem" }}>
          <strong>Demo accounts</strong> (password: <code>Frontdesk@123</code>):
          <div className="row" style={{ marginTop: 8 }}>
            <button type="button" className="btn btn-sm" onClick={() => fill("meera@arvo.test")}>
              Fill Manager (Meera)
            </button>
            <button type="button" className="btn btn-sm" onClick={() => fill("agent1@arvo.test")}>
              Fill Agent 1
            </button>
            <button type="button" className="btn btn-sm" onClick={() => fill("agent2@arvo.test")}>
              Fill Agent 2
            </button>
          </div>
        </div>

        <p style={{ marginTop: 16, marginBottom: 0 }}>
          Are you a customer? <Link to="/portal">Open Customer Portal →</Link>
        </p>
      </div>
    </div>
  );
}