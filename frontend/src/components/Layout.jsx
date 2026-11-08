import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useApp } from '../context'

export default function Layout() {
  const { user, logout, compare, toast } = useApp()
  const nav = useNavigate()
  const owner = user?.role === 'owner'
  const items = owner
    ? [['/owner', '🏨', 'My hostels', true], ['/owner/new', '➕', 'Add hostel', false]]
    : [['/', '🔍', 'Search', true], ['/compare', '⚖️', `Compare${compare.length ? ` (${compare.length})` : ''}`, false], ['/feedback', '📝', 'Feedback', false]]
  return (
    <div className="app">
      {toast && <div className="toast">{toast}</div>}
      <Outlet />
      <nav className="nav">
        <span className="nav-brand">🏠 CampusNest</span>
        {items.map(([to, ico, label, end]) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'active' : '')}>
            <span className="ico">{ico}</span>{label}
          </NavLink>
        ))}
        <span className="nav-user">Hi, {user?.name?.split(' ')[0]}</span>
        <button onClick={() => { logout(); nav('/login') }}><span className="ico">👤</span>Log out</button>
      </nav>
    </div>
  )
}
