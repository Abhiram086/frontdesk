import { Link, Navigate, useNavigate } from "react-router-dom";

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

export function RequireAuth({ manager = false, children }) {
  const token = localStorage.getItem("token");
  const user = getUser();
  if (!token || !user) return <Navigate to="/login" replace />;
  if (manager && user.role !== "manager") return <Navigate to="/tickets" replace />;
  return children;
}

export function TopBar() {
  const user = getUser();
  const navigate = useNavigate();

  function handleLogout() {
    clearAuth();
    navigate("/login");
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <Link to="/tickets" className="brand">Frontdesk</Link>
        <nav className="nav-links">
          <Link to="/tickets">Tickets</Link>
          {user?.role === "manager" && <Link to="/manager/late">Late report</Link>}
          <Link to="/portal">Customer portal</Link>
        </nav>
      </div>
      <div className="topbar-right">
        <span className="user-pill">{user?.name} ({user?.role})</span>
        <button className="btn btn-sm" onClick={handleLogout}>Logout</button>
      </div>
    </header>
  );
}