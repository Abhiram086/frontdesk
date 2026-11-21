export function fmtMin(m) {
  const a = Math.abs(Math.round(m));
  const h = Math.floor(a / 60);
  const mm = a % 60;
  const text = h ? `${h}h ${mm}m` : `${mm}m`;
  return m < 0 ? `Late by ${text}` : `${text} left`;
}

export function ist(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" });
}