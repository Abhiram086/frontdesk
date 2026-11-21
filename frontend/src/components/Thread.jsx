import { ist } from "../format";

export default function Thread({ items }) {
  if (!items.length) return <p className="muted">No messages yet.</p>;

  return (
    <div className="thread">
      {items.map((item) => {
        if (item.kind === "note") {
          return (
            <div key={`${item.src}-${item.id}`} className="bubble bubble-note">
              <div className="bubble-meta">
                <span>🔒 Team only. Never shown to the customer</span>
                <span>{item.author} · {ist(item.created_at)}</span>
              </div>
              <div className="bubble-body">{item.body}</div>
            </div>
          );
        }

        const isCustomer = item.kind === "customer";
        return (
          <div
            key={`${item.src}-${item.id}`}
            className={`bubble ${isCustomer ? "bubble-customer" : "bubble-agent"}`}
          >
            <div className="bubble-meta">
              <strong>{isCustomer ? "Customer" : item.author || "Agent"}</strong>
              <span>{ist(item.created_at)}</span>
            </div>
            <div className="bubble-body">{item.body}</div>
          </div>
        );
      })}
    </div>
  );
}