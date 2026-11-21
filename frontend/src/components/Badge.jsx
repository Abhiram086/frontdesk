export default function Badge({ text, tone = "grey" }) {
  return <span className={`badge badge-${tone}`}>{text}</span>;
}