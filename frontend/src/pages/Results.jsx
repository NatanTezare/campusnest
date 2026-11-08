import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, kes } from '../api'
import { useApp } from '../context'
import Hero from '../components/Hero'
import { photoStyle } from '../components/bits'

export default function Results() {
  const { prefs, compare, toggleCompare, setScores } = useApp()
  const nav = useNavigate()
  const [list, setList] = useState(null)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(null) // hostel whose "why this match?" is expanded

  useEffect(() => {
    api.post('/hostels/recommend', prefs)
      .then((r) => { setList(r); setScores(Object.fromEntries(r.map((h) => [h.id, h.score]))) })
      .catch((e) => setError(e.message))
  }, [prefs, setScores])

  return (<>
    <Hero back="Edit search" backTo="/" title="Top matches"
      sub={`${prefs.room_type} · up to ${kes(prefs.budget)} · ${prefs.max_distance_km} km · ${prefs.amenities.join(', ') || 'any amenities'}`} />
    <div className="wrap">
      {error && <div className="error">{error}</div>}
      {!list && !error && <div className="center">Finding your best matches…</div>}
      <div className="grid-cards">
      {list?.map((h) => (
        <div className="card" key={h.id}>
          <div className="ph" style={photoStyle(h)} onClick={() => nav(`/hostel/${h.id}`)}>{!h.photos.length && '🏠'}</div>
          <div className="pad">
            <div className="row">
              <Link to={`/hostel/${h.id}`} style={{ color: 'var(--blue)', fontWeight: 700, textDecoration: 'none' }}>{h.name}</Link>
              <span className="pill">{h.score}% match</span>
            </div>
            <div className="muted"><span className="price">{kes(h.best_room.price)}</span> · {h.best_room.name}{!h.best_room.available && ' (full)'} · {h.distance_km} km · ★ {h.avg_rating ?? '–'} ({h.review_count})</div>
            {h.rooms.length > 1 && (
              <div className="chips" style={{ marginTop: 6 }}>
                {h.rooms.map((r) => <span key={r.id} className="chip static" style={{ fontSize: 11, padding: '3px 9px', opacity: r.available ? 1 : .5, textDecoration: r.available ? 'none' : 'line-through' }}>{r.name} {kes(r.price)}</span>)}
              </div>
            )}
            <div className="muted" style={{ margin: '6px 0' }}>{h.amenities.join(' • ') || 'No amenities listed'}</div>
            <button className="link" onClick={() => setOpen(open === h.id ? null : h.id)}>{open === h.id ? '▲ Hide' : '▼ Why this match?'}</button>
            {open === h.id && <ul className="why">{h.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 600, margin: '4px 0 0' }}>
              <input type="checkbox" checked={compare.includes(h.id)} onChange={() => toggleCompare(h.id)} /> Add to compare
            </label>
          </div>
        </div>
      ))}
      </div>
    </div>
    {compare.length >= 2 && (
      <div className="cmpbar"><button className="btn gold" style={{ margin: 0 }} onClick={() => nav('/compare')}>Compare {compare.length} selected →</button></div>
    )}
  </>)
}
