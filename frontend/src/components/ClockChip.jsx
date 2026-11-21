import { fmtMin } from "../format";

export default function ClockChip({ clock }) {
  if (!clock) return <span className="badge badge-grey">—</span>;
  if (clock.state === "stopped") return <span className="badge badge-grey">Done</span>;
  if (clock.state === "paused") return <span className="badge badge-amber">Paused</span>;

  const isLate = clock.remaining_min < 0;
  return (
    <span className={`badge ${isLate ? "badge-red" : "badge-green"}`}>
      {fmtMin(clock.remaining_min)}
    </span>
  );
}