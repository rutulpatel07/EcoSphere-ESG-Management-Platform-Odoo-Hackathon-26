import { NavLink } from "react-router-dom";

// Navigation items per the wireframe sidebar.
const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/environmental", label: "Environmental", icon: "🌱" },
  { to: "/social", label: "Social", icon: "🤝" },
  { to: "/governance", label: "Governance", icon: "⚖️" },
  { to: "/gamification", label: "Gamification", icon: "🏆" },
  { to: "/reports", label: "Reports", icon: "📑" },
  { to: "/settings", label: "Settings", icon: "⚙️" },
];

export default function Sidebar() {
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
            className={({ isActive }) =>
              "sidebar-link" + (isActive ? " sidebar-link--active" : "")
            }
          >
            <span className="sidebar-link-icon">{item.icon}</span>
            <span className="sidebar-link-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">ESG Management Platform</div>
    </aside>
  );
}
