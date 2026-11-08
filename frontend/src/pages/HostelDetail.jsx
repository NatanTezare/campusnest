import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, fileUrl, kes } from '../api'
import { useApp } from '../context'
import Hero from '../components/Hero'
import { AvailabilityPill, Stars, photoStyle } from '../components/bits'

export default function HostelDetail() {
  const { id } = useParams()
  const { user, compare, toggleCompare, notify } = useApp()
  const [h, setH] = useState(null)
  const [error, setError] = useState('')
  const [rating, setRating] = useState(4)
  const [comment, setComment] = useState('')
  const [showReview, setShowReview] = useState(false)
  const [flagging, setFlagging] = useState(false)
  const [reason, setReason] = useState('')

  const load = useCallback(() => api.get(`/hostels/${id}`).then(setH).catch((e) => setError(e.message)), [id])
  useEffect(() => { load() }, [load])

  async function submitReview(e) {
    e.preventDefault()
    try {
      await api.post(`/hostels/${id}/reviews`, { rating, comment })
      notify('Review posted ⭐'); setShowReview(false); setComment(''); load()
    } catch (err) { notify(err.message) }
  }
  async function submitFlag(e) {
    e.preventDefault()
    try {
      const r = await api.post(`/hostels/${id}/flag`, { reason })
      notify(r.detail); setFlagging(false); setReason(''); load()
    } catch (err) { notify(err.message) }
  }

  if (error) return <div className="center">{error}</div>
  if (!h) return <div className="center">Loading…</div>
  const student = user.role === 'student'
  const mine = user.role === 'owner' && h.owner_id === user.id

  return (<>
    <Hero back="Back" title={h.name}
      sub={`from ${kes(h.price_from)} per person / month · ${h.distance_km} km from campus${h.location ? ` · ${h.location}` : ''}`} />
    <div className="wrap detail-grid">
      <div className="dg-left">
      <div className="dg-main">
        <div className="gallery">
          {(h.photos.length ? h.photos : [null]).map((_, i) => (
            <div key={i} style={photoStyle(h, i)}>{!h.photos.length && '🏠'}</div>
          ))}
        </div>
        <div className="row" style={{ margin: '14px 0' }}>
          <span><Stars value={h.avg_rating} /> <b>{h.avg_rating ?? '–'}</b> <span className="muted">({h.review_count} review{h.review_count !== 1 ? 's' : ''})</span></span>
          <AvailabilityPill available={h.available} />
        </div>
        <div className="chips">{h.amenities.map((a) => <span key={a} className="chip static">✓ {a}</span>)}</div>
      </div>

      <div className="dg-info">
        {h.description && <p style={{ fontSize: 14 }}>{h.description}</p>}
        {h.contact_phone && <p className="muted">📞 Owner contact: <b>{h.contact_phone}</b></p>}
      </div>

      <div className="dg-actions">
        {student && (<>
          <button className="btn gold" onClick={() => toggleCompare(h.id)}>
            {compare.includes(h.id) ? '✓ Added to compare (tap to remove)' : '⚖️ Add to compare'}
          </button>
          {compare.length >= 2 && <Link className="btn ghost" to="/compare">Go to comparison ({compare.length})</Link>}
          <button className="btn" onClick={() => setShowReview(!showReview)}>✍️ Rate or review this hostel</button>
          {showReview && (
            <form className="card pad" style={{ marginTop: 12 }} onSubmit={submitReview}>
              <div className="star-input">
                {[1, 2, 3, 4, 5].map((i) => <span key={i} onClick={() => setRating(i)}>{i <= rating ? '★' : '☆'}</span>)}
              </div>
              <label>Your review</label>
              <textarea rows={4} required minLength={3} value={comment} onChange={(e) => setComment(e.target.value)}
                placeholder="Tell other students what it is really like…" />
              <button className="btn">Submit review</button>
            </form>
          )}
          <button className="link" onClick={() => setFlagging(!flagging)}>⚑ Flag this listing as inaccurate</button>
          {flagging && (
            <form onSubmit={submitFlag}>
              <input type="text" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="What is wrong? (e.g. price is outdated)" />
              <button className="btn ghost">Send report</button>
            </form>
          )}
        </>)}
        {mine && <>
          {h.flag_count > 0 && <div className="error">⚑ {h.flag_count} student{h.flag_count > 1 ? 's have' : ' has'} flagged this listing. Please check the details.</div>}
          <Link className="btn" to={`/owner/${h.id}/edit`}>✏️ Edit this listing</Link>
        </>}
      </div>
      </div>
      <div className="dg-right">
      <div className="dg-rooms">
        <h2>Rooms &amp; prices</h2>
        <div className="card">
          {h.rooms.map((r, i) => (
            <div className="row pad" key={r.id} style={{ borderTop: i ? '1px solid var(--line)' : 0 }}>
              <div><b style={{ color: 'var(--blue)' }}>{r.name}</b><div className="muted">per person / month</div></div>
              <div style={{ textAlign: 'right' }}><div className="price">{kes(r.price)}</div>
                <span className={`pill ${r.available ? 'green' : 'red'}`} style={{ fontSize: 10 }}>{r.available ? 'Available' : 'Full'}</span></div>
            </div>
          ))}
        </div>
      </div>

      <div className="dg-reviews">
        <h2>Reviews ({h.review_count})</h2>
        {h.reviews.length === 0 && <div className="muted">No reviews yet. Be the first to rate this hostel.</div>}
        {h.reviews.map((r) => (
          <div className="card pad" key={r.id}>
            <b style={{ color: 'var(--blue)' }}>{r.student_name}</b> <Stars value={r.rating} />
            <div className="muted" style={{ marginTop: 4 }}>{r.comment}</div>
          </div>
        ))}
      </div>
      </div>
    </div>
  </>)
}
