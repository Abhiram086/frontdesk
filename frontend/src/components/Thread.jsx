import { initials } from "../auth";
import { ist } from "../format";

export default function Thread({ items }) {
  if (!items.length) return <p className="muted">No messages yet.</p>;

  return (
    <div className="thread">
      {items.map((item) => {
        if (item.kind === "note") {
          return (
            <div key={`${item.src}-${item.id}`} className="note-box">
              <div className="msg-head">
                <span>🔒 Team only · Never shown to the customer</span>
                <span className="msg-time">{item.author} · {ist(item.created_at)}</span>
              </div>
              <div className="msg-body">{item.body}</div>
            </div>
          );
        }

        const isCustomer = item.kind === "customer";
        const name = isCustomer ? "Customer" : item.author || "Agent";
        return (
          <div key={`${item.src}-${item.id}`} className="msg-row">
            <span className={`avatar ${isCustomer ? "" : "avatar-dark"}`}>
              {isCustomer ? "C" : initials(name)}
            </span>
            <div className="msg-content">
              <div className="msg-head">
                <strong>{name}</strong>
                <span className="msg-time">{ist(item.created_at)}</span>
              </div>
              <div className="msg-body">{item.body}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}