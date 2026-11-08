import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AMENITIES, ROOM_TYPES, api, kes } from '../api'
import { useApp } from '../context'
import Hero from '../components/Hero'
import { AmenityChips } from '../components/bits'

export default function Search() {
  const { prefs, setPrefs } = useApp()
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [matches, setMatches] = useState(null)

  // Live search by hostel name (debounced)
  useEffect(() => {
    if (!q.trim()) { setMatches(null); return }
    const t = setTimeout(() => api.get(`/hostels?q=${encodeURIComponent(q.trim())}`).then(setMatches).catch(() => setMatches([])), 250)
    return () => clearTimeout(t)
  }, [q])

  const toggleAmenity = (a) => setPrefs({ ...prefs, amenities: prefs.amenities.includes(a) ? prefs.amenities.filter((x) => x !== a) : [...prefs.amenities, a] })

  return (<>
    <Hero brand="🏠 CAMPUSNEST" title="What matters to you?" sub="We'll rank the best matches." />
    <div className="wrap split">
      <div className="panel">
      <label style={{ marginTop: 0 }}>🔎 Find a hostel by name</label>
      <input type="text" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Roysambu Heights" />
      {matches && (
        <div style={{ marginTop: 10 }}>
          {matches.length === 0 && <div className="muted">No hostel named “{q}” yet. Ask the owner to list it.</div>}
          {matches.map((h) => (
            <Link key={h.id} to={`/hostel/${h.id}`} style={{ textDecoration: 'none' }}>
              <div className="card pad row" style={{ marginBottom: 8 }}>
                <div>
                  <b style={{ color: 'var(--blue)' }}>{h.name}</b>
                  <div className="muted">from {kes(h.price_from)} · {h.distance_km} km · ★ {h.avg_rating ?? '–'} ({h.review_count}){!h.available && ' · 🔴 Fully booked'}</div>
                </div>
                <span className="pill">Open ›</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      <div className="muted or-divider">— or match hostels to your preferences —</div>
      </div>
      <div className="panel">
      <label>Max budget: <span className="price">{kes(prefs.budget)}</span> per person / month</label>
      <input type="range" min="3000" max="30000" step="500" value={prefs.budget}
        onChange={(e) => setPrefs({ ...prefs, budget: +e.target.value })} />
      <label>Max distance: <span className="price">{prefs.max_distance_km} km</span></label>
      <input type="range" min="0.3" max="5" step="0.1" value={prefs.max_distance_km}
        onChange={(e) => setPrefs({ ...prefs, max_distance_km: +e.target.value })} />
      <label>Room type</label>
      <div className="chips">
        {['Any', ...ROOM_TYPES].map((t) => (
          <button type="button" key={t} className={`chip ${prefs.room_type === t ? 'on' : ''}`}
            onClick={() => setPrefs({ ...prefs, room_type: t })}>{t}</button>
        ))}
      </div>
      <label>Must-have amenities</label>
      <AmenityChips items={AMENITIES} selected={prefs.amenities} onToggle={toggleAmenity} />
      <button className="btn" onClick={() => nav('/results')}>🔍 Find hostels</button>
      </div>
    </div>
  </>)
}
