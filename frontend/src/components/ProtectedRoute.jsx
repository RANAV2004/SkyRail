import { Navigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import Navbar from "./Navbar.jsx";

export default function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="container muted">Loading…</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (role && user.role !== role) {
    return <Navigate to={user.role === "admin" ? "/admin" : "/"} replace />;
  }

  return (
    <div className="shell">
      <Navbar />
      <main className="main">{children}</main>
    </div>
  );
}
