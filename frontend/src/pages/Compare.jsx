import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AMENITIES, ROOM_TYPES, api, kes } from '../api'
import { useApp } from '../context'
import Hero from '../components/Hero'

export default function Compare() {
  const { compare, toggleCompare, scores } = useApp()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setData(null); setError('')
    if (compare.length < 2) return
    api.get(`/hostels/compare?ids=${compare.join(',')}`).then(setData).catch((e) => setError(e.message))
  }, [compare])

  if (compare.length < 2) return (<>
    <Hero title="Compare" sub="Pick at least 2 hostels from the results." />
    <div className="wrap"><Link className="btn" to="/results">Browse hostels</Link></div>
  </>)

  const hs = data?.hostels || []
  const cls = (key, h) => (data?.best[key] === h.id ? 'best' : '')
  const roomOf = (h, type) => h.rooms.find((r) => r.name === type)
  const cheapest = (type) => Math.min(...hs.map((h) => roomOf(h, type)?.price ?? Infinity))
  const types = ROOM_TYPES.filter((t) => hs.some((h) => roomOf(h, t)))
  return (<>
    <Hero title="Side by side" sub="Best value in each row is highlighted." />
    <div className="wrap">
      {error && <div className="error">{error}</div>}
      {data && (
        <div className="card" style={{ overflowX: 'auto' }}>
          <table className="tbl">
            <thead><tr><th></th>{hs.map((h) => (
              <th key={h.id}>{h.name}<br /><button className="back" style={{ fontSize: 11, opacity: .8 }} onClick={() => toggleCompare(h.id)}>✕ remove</button></th>
            ))}</tr></thead>
            <tbody>
              <tr><td>Price from</td>{hs.map((h) => <td key={h.id} className={cls('price', h)}>{kes(h.price_from)}</td>)}</tr>
              {types.map((t) => (
                <tr key={t}><td>{t}</td>{hs.map((h) => {
                  const r = roomOf(h, t)
                  return <td key={h.id} className={r && r.price === cheapest(t) ? 'best' : ''} style={r && !r.available ? { opacity: .5 } : null}>
                    {r ? <>{kes(r.price)}{!r.available && <div style={{ fontSize: 10 }}>full</div>}</> : '—'}</td>
                })}</tr>
              ))}
              <tr><td>Distance</td>{hs.map((h) => <td key={h.id} className={cls('distance', h)}>{h.distance_km} km</td>)}</tr>
              <tr><td>Rating</td>{hs.map((h) => <td key={h.id} className={cls('rating', h)}>{h.avg_rating ? `★ ${h.avg_rating}` : '–'}</td>)}</tr>
              {hs.some((h) => scores[h.id] != null) && (
                <tr><td>Match</td>{hs.map((h) => <td key={h.id}>{scores[h.id] != null ? `${scores[h.id]}%` : '–'}</td>)}</tr>
              )}
              <tr><td>Status</td>{hs.map((h) => <td key={h.id}>{h.available ? 'Available' : 'Fully booked'}</td>)}</tr>
              {AMENITIES.map((a) => <tr key={a}><td>{a}</td>{hs.map((h) => <td key={h.id}>{h.amenities.includes(a) ? '✅' : '—'}</td>)}</tr>)}
            </tbody>
          </table>
        </div>
      )}
      <Link className="btn ghost" to="/results">Browse more hostels</Link>
    </div>
  </>)
}
