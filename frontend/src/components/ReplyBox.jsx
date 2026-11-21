import { useState } from "react";

export default function ReplyBox({ disabled, onSendReply, onSendNote }) {
  const [tab, setTab] = useState("reply");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(waitForCustomer = false) {
    const text = body.trim();
    if (!text) return;
    setBusy(true);
    try {
      if (tab === "note") {
        await onSendNote(text);
      } else {
        await onSendReply(text, waitForCustomer);
      }
      setBody("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`composer ${tab === "note" ? "composer-note" : ""}`}>
      <div className="tabs">
        <button
          type="button"
          className={`tab ${tab === "reply" ? "active" : ""}`}
          onClick={() => setTab("reply")}
        >
          Reply to customer
        </button>
        <button
          type="button"
          className={`tab ${tab === "note" ? "active tab-note" : ""}`}
          onClick={() => setTab("note")}
        >
          🔒 Internal note
        </button>
      </div>

      {tab === "note" && (
        <div className="note-warning">
          Private team note — never sent to or visible by the customer.
        </div>
      )}

      <textarea
        rows={4}
        disabled={disabled || busy}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={
          tab === "note"
            ? "Write a note for your team..."
            : "Write your reply to the customer..."
        }
      />

      <div className="composer-actions">
        {tab === "note" ? (
          <button
            className="btn btn-warning"
            disabled={disabled || busy || !body.trim()}
            onClick={() => submit(false)}
          >
            Add internal note
          </button>
        ) : (
          <>
            <button
              className="btn btn-primary"
              disabled={disabled || busy || !body.trim()}
              onClick={() => submit(false)}
            >
              Send
            </button>
            <button
              className="btn"
              disabled={disabled || busy || !body.trim()}
              onClick={() => submit(true)}
            >
              Send and wait for customer
            </button>
          </>
        )}
      </div>
    </div>
  );
}