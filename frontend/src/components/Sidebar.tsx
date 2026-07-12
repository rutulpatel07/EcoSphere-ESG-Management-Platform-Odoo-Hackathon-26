import { NavLink, useNavigate } from "react-router-dom";
import { getSessionUser, logout } from "../auth";

// Navigation items per the wireframe sidebar. `pillar` drives the accent color:
// green = Environmental, blue = Social, purple = Governance, orange = Gamification.
const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊", pillar: "overview" },
  { to: "/environmental", label: "Environmental", icon: "🌱", pillar: "e" },
  { to: "/social", label: "Social", icon: "🤝", pillar: "s" },
  { to: "/governance", label: "Governance", icon: "⚖️", pillar: "g" },
  { to: "/gamification", label: "Gamification", icon: "🏆", pillar: "gamification" },
  { to: "/reports", label: "Reports", icon: "📑", pillar: "neutral" },
  { to: "/settings", label: "Settings", icon: "⚙️", pillar: "neutral" },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const user = getSessionUser();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">🌍</span>
        <span className="sidebar-brand-name">EcoSphere</span>
      </div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            data-pillar={item.pillar}
            className={({ isActive }) =>
              "sidebar-link" + (isActive ? " sidebar-link--active" : "")
            }
          >
            <span className="sidebar-link-icon">{item.icon}</span>
            <span className="sidebar-link-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      {user && (
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">{user.full_name.charAt(0)}</div>
          <div className="sidebar-user-meta">
            <div className="sidebar-user-name">{user.full_name}</div>
            <div className="sidebar-user-role">{user.role}</div>
          </div>
          <button type="button" className="sidebar-logout" onClick={handleLogout} title="Sign out">
            ⎋
          </button>
        </div>
      )}
      <div className="sidebar-footer">ESG Management Platform</div>
    </aside>
  );
}
