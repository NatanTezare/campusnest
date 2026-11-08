import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, kes } from '../api'
import { useApp } from '../context'
import Hero from '../components/Hero'
import { AvailabilityPill, photoStyle } from '../components/bits'

export default function Dashboard() {
  const { notify } = useApp()
  const [list, setList] = useState(null)
  const [open, setOpen] = useState(null) // hostel whose student reports are showing
  const [flags, setFlags] = useState([])
  const [error, setError] = useState('')
  useEffect(() => { api.get('/hostels/mine').then(setList).catch((e) => setError(e.message)) }, [])

  async function toggleReports(h) {
    if (open === h.id) return setOpen(null)
    try { setFlags(await api.get(`/hostels/${h.id}/flags`)); setOpen(h.id) } catch (e) { notify(e.message) }
  }
  async function clearReports(h) {
    try {
      const updated = await api.post(`/hostels/${h.id}/flags/resolve`)
      setList(list.map((x) => (x.id === h.id ? updated : x))); setOpen(null); notify('Reports cleared ✅')
    } catch (e) { notify(e.message) }
  }

  return (<>
    <Hero brand="🔑 OWNER DASHBOARD" title="My hostels" sub="Update prices and availability anytime." />
    <div className="wrap">
      <Link className="btn gold inline" style={{ marginTop: 0 }} to="/owner/new">➕ Add new hostel</Link>
      {error && <div className="error">{error}</div>}
      {!list && !error && <div className="center">Loading…</div>}
      {list?.length === 0 && <div className="center">You have not listed a hostel yet.</div>}
      <div className="grid-cards" style={{ marginTop: 16 }}>
        {list?.map((h) => (
          <div className="card" key={h.id}>
            <div className="ph" style={photoStyle(h)}>{!h.photos.length && '🏠'}</div>
            <div className="pad">
              <div className="row"><b style={{ color: 'var(--blue)' }}>{h.name}</b><AvailabilityPill available={h.available} /></div>
              <div className="muted"><span className="price">from {kes(h.price_from)}</span> · {h.rooms.length} room type{h.rooms.length > 1 ? 's' : ''} · {h.distance_km} km · ★ {h.avg_rating ?? '–'} ({h.review_count})</div>
              {h.flag_count > 0 && (
                <button className="link" style={{ color: 'var(--danger)', fontWeight: 700 }} onClick={() => toggleReports(h)}>
                  ⚑ {h.flag_count} report{h.flag_count > 1 ? 's' : ''} from students · {open === h.id ? 'hide' : 'view'}
                </button>
              )}
              {open === h.id && (
                <div style={{ background: '#FDE8E8', borderRadius: 12, padding: '10px 12px', marginTop: 4 }}>
                  <ul className="why" style={{ margin: 0 }}>{flags.map((f) => <li key={f.id}>{f.reason || 'No reason given'}</li>)}</ul>
                  <p className="muted" style={{ margin: '8px 0 0' }}>Fix the listing (price, availability…), then clear the reports.</p>
                  <Link className="btn ghost" style={{ marginTop: 10 }} to={`/owner/${h.id}/edit`}>✏️ Edit listing</Link>
                  <button className="btn" style={{ marginTop: 8 }} onClick={() => clearReports(h)}>✔ I've fixed it, clear reports</button>
                </div>
              )}
              <Link className="btn ghost" to={`/owner/${h.id}/edit`}>✏️ Edit listing</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  </>)
}
