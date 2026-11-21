import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const SEVERITIES = [
  { value: "critical", label: "I cannot work at all", hint: "Critical — reply in 2h, same working day fix" },
  { value: "medium", label: "Something is not working properly", hint: "Medium — reply in half a day, fix in ~3 days" },
  { value: "low", label: "A question or small request", hint: "Low — reply in 1 day, fix in ~1 week" },
];

export default function PortalNew() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [priority, setPriority] = useState("medium");
  const [createdToken, setCreatedToken] = useState("");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const saved = JSON.parse(localStorage.getItem("portal_tickets") || "[]");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api("/public/tickets", {
        method: "POST",
        body: { name, email, subject, body, priority },
      });
      const updated = [{ token: res.token, subject }, ...saved].slice(0, 10);
      localStorage.setItem("portal_tickets", JSON.stringify(updated));
      setCreatedToken(res.token);
      setSubject("");
      setBody("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const fullUrl = createdToken ? `${window.location.origin}/portal/t/${createdToken}` : "";

  function copyLink() {
    navigator.clipboard.writeText(fullUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="container narrow">
      <div className="banner banner-warn space-between">
        <span>Customer simulator: this is what Arvo&apos;s customers see.</span>
        <Link to="/login">Staff Login →</Link>
      </div>

      {createdToken ? (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Ticket submitted!</h2>
          <p>Save this private link to view replies and follow up:</p>
          <input readOnly value={fullUrl} style={{ marginBottom: 12 }} />
          <div className="row">
            <button className="btn btn-primary" onClick={copyLink}>
              {copied ? "Copied!" : "Copy link"}
            </button>
            <Link className="btn" to={`/portal/t/${createdToken}`}>
              Open ticket
            </Link>
            <button className="btn" onClick={() => setCreatedToken("")}>
              Raise another
            </button>
          </div>
        </div>
      ) : (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Contact Arvo Support</h2>
          {error && <div className="error">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="grid-2">
              <div className="field">
                <label>Your name</label>
                <input required value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="field">
                <label>Email address</label>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
            </div>

            <div className="field">
              <label>Subject</label>
              <input required value={subject} onChange={(e) => setSubject(e.target.value)} />
            </div>

            <div className="field">
              <label>How urgent is this?</label>
              {SEVERITIES.map((s) => (
                <label key={s.value} className="radio-option">
                  <input
                    type="radio"
                    name="priority"
                    checked={priority === s.value}
                    onChange={() => setPriority(s.value)}
                  />
                  <div>
                    <div style={{ fontWeight: 600 }}>{s.label}</div>
                    <div className="muted" style={{ fontSize: "0.82rem" }}>{s.hint}</div>
                  </div>
                </label>
              ))}
            </div>

            <div className="field">
              <label>Describe the problem</label>
              <textarea rows={5} required value={body} onChange={(e) => setBody(e.target.value)} />
            </div>

            <button className="btn btn-primary" disabled={busy}>
              {busy ? "Submitting..." : "Submit ticket"}
            </button>
          </form>
        </div>
      )}

      {saved.length > 0 && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Your recent tickets (this browser)</h3>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {saved.map((item) => (
              <li key={item.token} style={{ marginBottom: 6 }}>
                <Link to={`/portal/t/${item.token}`}>{item.subject}</Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}