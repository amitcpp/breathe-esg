import { NavLink, Outlet, useNavigate } from 'react-router-dom'

export default function Layout() {
  const navigate = useNavigate()

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/login')
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>Breathe ESG</h1>
          <span>Emissions Intelligence</span>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <span className="icon">📊</span>
            Dashboard
          </NavLink>
          <NavLink to="/upload" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <span className="icon">📁</span>
            Upload Data
          </NavLink>
          <NavLink to="/review" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <span className="icon">✅</span>
            Review Queue
          </NavLink>
          <div style={{ flex: 1 }} />
          <button className="nav-link" onClick={handleLogout}>
            <span className="icon">🚪</span>
            Sign Out
          </button>
        </nav>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
