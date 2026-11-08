import { Navigate, Route, Routes } from 'react-router-dom'
import { useApp } from './context'
import Layout from './components/Layout'
import Login from './pages/Login'
import Search from './pages/Search'
import Results from './pages/Results'
import HostelDetail from './pages/HostelDetail'
import Compare from './pages/Compare'
import Dashboard from './pages/Dashboard'
import HostelForm from './pages/HostelForm'
import Feedback from './pages/Feedback'

/** Only lets the given role through; everyone else is redirected to their own home page. */
function Guard({ role, children }) {
  const { user, ready } = useApp()
  if (!ready) return <div className="center">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role) return <Navigate to={user.role === 'owner' ? '/owner' : '/'} replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Guard><Layout /></Guard>}>
        <Route path="/" element={<Guard role="student"><Search /></Guard>} />
        <Route path="/results" element={<Guard role="student"><Results /></Guard>} />
        <Route path="/compare" element={<Guard role="student"><Compare /></Guard>} />
        <Route path="/feedback" element={<Guard role="student"><Feedback /></Guard>} />
        <Route path="/hostel/:id" element={<HostelDetail />} />
        <Route path="/owner" element={<Guard role="owner"><Dashboard /></Guard>} />
        <Route path="/owner/new" element={<Guard role="owner"><HostelForm /></Guard>} />
        <Route path="/owner/:id/edit" element={<Guard role="owner"><HostelForm /></Guard>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
