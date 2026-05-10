import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/auth-context";

const publicNavItems = [
  { href: "/", label: "Home", icon: "bi-house" },
  { href: "/about", label: "About", icon: "bi-info-circle" },
  { href: "/contact", label: "Contact", icon: "bi-envelope" },
];

const authNavItems = [
  { href: "/dashboard", label: "Dashboard", icon: "bi-grid-1x2" },
  { href: "/about", label: "About", icon: "bi-info-circle" },
  { href: "/contact", label: "Contact", icon: "bi-envelope" },
];

export function SiteHeader() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isDashboard = location.pathname.startsWith("/dashboard");

  const navItems = user ? authNavItems : publicNavItems;

  if (isDashboard) {
    return null;
  }

  return (
    <nav className="navbar navbar-expand-lg cs-navbar">
      <div className="container">
        <Link to="/" className="navbar-brand brand">
          <span className="brand-mark">
            <i className="bi bi-heart-pulse-fill" />
          </span>
          CardioSense <span className="brand-accent">AI</span>
        </Link>
        <button
          className="navbar-toggler"
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-controls="mainNav"
          aria-expanded={mobileOpen}
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon" />
        </button>
        <div
          className={`collapse navbar-collapse ${mobileOpen ? "show" : ""}`}
          id="mainNav"
        >
          <ul className="navbar-nav ms-auto align-items-lg-center gap-lg-1">
            {navItems.map((item) => {
              const active = location.pathname === item.href;
              return (
                <li className="nav-item" key={item.href}>
                  <Link
                    to={item.href}
                    className={`nav-link ${active ? "active" : ""}`}
                  >
                    <i className={item.icon}></i> {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
          <div className="d-flex flex-wrap gap-2 ms-lg-3 mt-3 mt-lg-0">
            {user ? (
              <>
                <span
                  className="d-flex align-items-center gap-2"
                  style={{
                    fontSize: "0.9rem",
                    color: "var(--ink-soft)",
                    fontWeight: 600,
                  }}
                >
                  <i className="bi bi-person-circle" />
                  {user.fullName}
                </span>
                <button
                  onClick={logout}
                  className="btn-outline-cs"
                  style={{ border: "none", background: "transparent" }}
                >
                  <i className="bi bi-box-arrow-right" /> Log Out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn-outline-cs">
                  <i className="bi bi-box-arrow-in-right" /> Log In
                </Link>
                <Link to="/signup" className="btn-primary-cs">
                  <i className="bi bi-person-plus" /> Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const menuItems = [
    { href: "/dashboard", label: "Overview", icon: "bi-grid-1x2-fill" },
    { href: "/dashboard/predict", label: "Predictor", icon: "bi-activity" },
    { href: "/dashboard/history", label: "History", icon: "bi-clock-history" },
    { href: "/dashboard/analytics", label: "Analytics", icon: "bi-graph-up" },
  ];

  if (!user) {
    navigate("/login");
    return null;
  }

  return (
    <div className="dashboard-layout">
      {/* Mobile top bar */}
      <div className="dashboard-mobile-topbar">
        <button
          className="sidebar-toggle-btn"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open menu"
        >
          <i className="bi bi-list"></i>
        </button>
        <span style={{ fontWeight: 700, fontSize: "1.1rem" }}>
          <i
            className="bi bi-heart-pulse-fill"
            style={{ color: "var(--primary)", marginRight: 6 }}
          />
          CardioSense
        </span>
        <span />
      </div>

      {/* Backdrop */}
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`dashboard-sidebar${sidebarOpen ? " open" : ""}`}>
        <div className="sidebar-header">
          <Link to="/" className="brand" onClick={() => setSidebarOpen(false)}>
            <span className="brand-mark">
              <i className="bi bi-heart-pulse-fill" />
            </span>
            CardioSense
          </Link>
          <button
            className="sidebar-close-btn"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close menu"
          >
            <i className="bi bi-x-lg"></i>
          </button>
        </div>

        <div className="sidebar-user">
          <div className="user-avatar">
            <i className="bi bi-person-circle"></i>
          </div>
          <div className="user-info">
            <span className="user-name">{user.fullName}</span>
            <span className="user-role">{user.role}</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {menuItems.map((item) => {
            const active = location.pathname === item.href;
            return (
              <Link
                key={item.href}
                to={item.href}
                className={`sidebar-link ${active ? "active" : ""}`}
                onClick={() => setSidebarOpen(false)}
              >
                <i className={item.icon}></i>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <button onClick={logout} className="sidebar-link logout">
            <i className="bi bi-box-arrow-right"></i>
            <span>Logout</span>
          </button>
        </div>
      </aside>

      <main className="dashboard-main">{children}</main>
    </div>
  );
}
