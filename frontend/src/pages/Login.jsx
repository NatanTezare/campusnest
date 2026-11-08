import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useApp } from '../context'
import Hero from '../components/Hero'

export default function Login() {
  const { user, authenticate } = useApp()
  const nav = useNavigate()
  const [mode, setMode] = useState('login')
  const [role, setRole] = useState('student')
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  if (user) return <Navigate to={user.role === 'owner' ? '/owner' : '/'} replace />

  async function submit(e) {
    e.preventDefault()
    setError(''); setBusy(true)
    try {
      const u = mode === 'login'
        ? await authenticate('/auth/login', { email: form.email, password: form.password })
        : await authenticate('/auth/register', { ...form, role })
      nav(u.role === 'owner' ? '/owner' : '/', { replace: true })
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <div className="app login-page">
      <div className="login-shell">
      <Hero brand="🏠 CAMPUSNEST" title={'Find your hostel,\nskip the walking.'} sub="Compare price, distance and amenities near USIU-Africa." />
      <form className="wrap login-form" onSubmit={submit}>
        <div className="chips">
          <button type="button" className={`chip ${mode === 'login' ? 'on' : ''}`} onClick={() => setMode('login')}>Log in</button>
          <button type="button" className={`chip ${mode === 'register' ? 'on' : ''}`} onClick={() => setMode('register')}>Create account</button>
        </div>
        {mode === 'register' && (<>
          <label>Full name</label>
          <input type="text" required minLength={2} value={form.name} onChange={set('name')} placeholder="Your name" />
          <label>I am a…</label>
          <div className="chips">
            <button type="button" className={`chip ${role === 'student' ? 'on' : ''}`} onClick={() => setRole('student')}>🎓 Student</button>
            <button type="button" className={`chip ${role === 'owner' ? 'on' : ''}`} onClick={() => setRole('owner')}>🔑 Hostel owner</button>
          </div>
        </>)}
        <label>Email</label>
        <input type="email" required value={form.email} onChange={set('email')} placeholder="you@usiu.ac.ke" />
        <label>Password</label>
        <input type="password" required minLength={6} value={form.password} onChange={set('password')} placeholder="••••••••" />
        {error && <div className="error">{error}</div>}
        <button className="btn" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}</button>
        <p className="muted" style={{ textAlign: 'center', marginTop: 16 }}>
          Demo: student@usiu.ac.ke / student123 · owner@usiu.ac.ke / owner123
        </p>
      </form>
      </div>
    </div>
  )
}
