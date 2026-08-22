import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function Shell() {
  const { user, logout } = useAuth();

  return (
    <div className="shell">
      <nav className="sidebar">
        <div className="brand">Medical Droid</div>
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
          Vitals
        </NavLink>
        <NavLink to="/teleop" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
          Camera / Drive
        </NavLink>
        <NavLink to="/door" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
          Door
        </NavLink>
        <div className="sidebar-footer">
          {user && <span className="user-chip">{user.username} · {user.role}</span>}
          <button className="btn btn-ghost" onClick={logout}>Sign Out</button>
        </div>
      </nav>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
