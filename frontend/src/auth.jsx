import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem("user") || "null");
  } catch {
    return null;
  }
}

export function saveAuth(token, user) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

export function initials(name = "?") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

export function RequireAuth({ manager = false, children }) {
  const token = localStorage.getItem("token");
  const user = getUser();
  if (!token || !user) return <Navigate to="/login" replace />;
  if (manager && user.role !== "manager") return <Navigate to="/tickets" replace />;
  return children;
}

export function AppShell({ children }) {
  const user = getUser();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const view = new URLSearchParams(search).get("view") || "mine";

  function handleLogout() {
    clearAuth();
    navigate("/login");
  }

  const isTickets = pathname === "/tickets";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <Link to="/tickets" className="brand-row">
            <span className="logo-mark">F</span>
            <span>Frontdesk</span>
          </Link>

          <nav className="side-nav">
            <Link
              to="/tickets?view=mine"
              className={`side-link ${isTickets && view === "mine" ? "active" : ""}`}
            >
              My Tickets
            </Link>
            <Link
              to="/tickets?view=unassigned"
              className={`side-link ${isTickets && view === "unassigned" ? "active" : ""}`}
            >
              Unassigned
            </Link>
            {user?.role === "manager" && (
              <>
                <Link
                  to="/tickets?view=all"
                  className={`side-link ${isTickets && view === "all" ? "active" : ""}`}
                >
                  All Tickets
                </Link>
                <Link
                  to="/manager/late"
                  className={`side-link ${pathname === "/manager/late" ? "active" : ""}`}
                >
                  Late Report
                </Link>
              </>
            )}
            <Link to="/portal" className="side-link">
              Customer Portal ↗
            </Link>
          </nav>
        </div>

        <div className="sidebar-footer">
          <div className="user-chip">
            <span className="avatar">{initials(user?.name)}</span>
            <div className="user-meta">
              <div className="user-name">{user?.name}</div>
              <div className="user-role">{user?.role}</div>
            </div>
          </div>
          <button className="btn btn-sm" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="main-area">{children}</main>
    </div>
  );
}