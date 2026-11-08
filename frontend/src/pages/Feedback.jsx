import { useEffect, useState } from 'react'
import { api } from '../api'
import { useApp } from '../context'
import Hero from '../components/Hero'

const Stat = ({ label, value }) => (
  <div style={{ background: 'var(--alice)', borderRadius: 14, padding: '10px 12px' }}>
    <div className="muted" style={{ fontSize: 11 }}>{label}</div>
    <div className="price" style={{ fontSize: 18 }}>{value}</div>
  </div>
)

/** Objective v: students tell us how long the old way took vs CampusNest, so we can measure time saved. */
export default function Feedback() {
  const { notify } = useApp()
  const [f, setF] = useState({ manual_hours: '', campusnest_minutes: '', ease: 0, would_recommend: null, comment: '' })
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [updated, setUpdated] = useState(false)

  const loadSummary = () => api.get('/feedback/summary').then(setSummary).catch(() => {})
  useEffect(() => {
    api.get('/feedback/mine').then((m) => {
      if (!m) return
      setF({ manual_hours: m.manual_hours ?? '', campusnest_minutes: m.campusnest_minutes, ease: m.ease,
        would_recommend: m.would_recommend, comment: m.comment || '' })
      setUpdated(true)
    }).catch(() => {})
    loadSummary()
  }, [])

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!f.ease) return setError('Please rate how easy it was (1 to 5).')
    if (f.would_recommend === null) return setError('Please choose Yes or No for "Would you recommend CampusNest?"')
    setBusy(true)
    try {
      await api.post('/feedback', {
        manual_hours: f.manual_hours === '' ? null : +f.manual_hours,
        campusnest_minutes: +f.campusnest_minutes, ease: f.ease,
        would_recommend: f.would_recommend, comment: f.comment.trim() || null,
      })
      notify('Thank you for your feedback! 🙏'); setUpdated(true); loadSummary()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (<>
    <Hero brand="📝 EVALUATION" title="Tell us how it went" sub="Your answers help us measure whether CampusNest really saves students time." />
    <div className="feedback-grid">
    <form className="wrap" onSubmit={submit}>
      <label style={{ marginTop: 0 }}>1. How many hours did it take you to find your hostel the old way (walking around, asking friends)? <span className="muted">Optional</span></label>
      <input type="number" min="0" max="500" step="0.5" value={f.manual_hours} onChange={set('manual_hours')} placeholder="e.g. 8" />

      <label>2. How many minutes did it take you to find a suitable hostel with CampusNest?</label>
      <input type="number" required min="0" max="600" value={f.campusnest_minutes} onChange={set('campusnest_minutes')} placeholder="e.g. 5" />

      <label>3. How easy was CampusNest to use?</label>
      <div className="chips scale">
        {[1, 2, 3, 4, 5].map((n) => (
          <button type="button" key={n} className={`chip ${f.ease === n ? 'on' : ''}`} style={{ minWidth: 46, textAlign: 'center' }}
            onClick={() => setF({ ...f, ease: n })}>{n}</button>
        ))}
      </div>
      <div className="row muted" style={{ marginTop: 4 }}><span>1 = very hard</span><span>5 = very easy</span></div>

      <label>4. Would you recommend CampusNest to a new student?</label>
      <div className="chips">
        <button type="button" className={`chip ${f.would_recommend === true ? 'on' : ''}`} onClick={() => setF({ ...f, would_recommend: true })}>Yes</button>
        <button type="button" className={`chip ${f.would_recommend === false ? 'on' : ''}`} onClick={() => setF({ ...f, would_recommend: false })}>No</button>
      </div>

      <label>5. Anything we should improve? <span className="muted">Optional</span></label>
      <textarea rows={3} value={f.comment} onChange={set('comment')} placeholder="What was confusing or missing?" />

      {error && <div className="error">{error}</div>}
      <button className="btn" disabled={busy}>{busy ? 'Sending…' : updated ? 'Update my feedback' : 'Send feedback'}</button>
    </form>

    {summary && summary.responses > 0 && (
      <div className="wrap fb-results">
        <div className="card pad">
          <h2 style={{ margin: '0 0 10px' }}>Results so far ({summary.responses} student{summary.responses > 1 ? 's' : ''})</h2>
          <div className="grid2">
            <Stat label="Average ease" value={`${summary.avg_ease} / 5`} />
            <Stat label="Would recommend" value={`${summary.would_recommend_pct}%`} />
            <Stat label="With CampusNest" value={`${summary.avg_campusnest_minutes} min`} />
            <Stat label="The old way" value={summary.avg_manual_hours != null ? `${summary.avg_manual_hours} hrs` : '–'} />
          </div>
          {summary.time_saved_pct != null && (
            <div style={{ marginTop: 12 }}><span className="pill green">⏱ {summary.time_saved_pct}% less time than the old way</span></div>
          )}
        </div>
      </div>
    )}
    </div>
  </>)
}
