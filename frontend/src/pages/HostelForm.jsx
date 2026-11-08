import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AMENITIES, ROOM_TYPES, api, fileUrl } from '../api'
import { useApp } from '../context'
import Hero from '../components/Hero'
import { AmenityChips } from '../components/bits'

const MAX_PHOTOS = 6
const blank = { name: '', location: '', distance_km: '', description: '', contact_phone: '', amenities: [] }
const firstRoom = { name: 'Single room', price: '', available: true }

/** Add (FR5) and edit a listing: details, room types with their own prices, amenities and photos. */
export default function HostelForm() {
  const { id } = useParams()
  const editing = Boolean(id)
  const nav = useNavigate()
  const { notify } = useApp()
  const fileInput = useRef(null)
  const [f, setF] = useState(blank)
  const [rooms, setRooms] = useState([firstRoom])
  const [existing, setExisting] = useState({ photos: [], ids: [] })
  const [files, setFiles] = useState([]) // newly chosen, not yet uploaded
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!editing) return
    api.get(`/hostels/${id}`).then((h) => {
      setF({ name: h.name, location: h.location || '', distance_km: h.distance_km, description: h.description || '',
        contact_phone: h.contact_phone || '', amenities: h.amenities })
      setRooms(h.rooms.map((r) => ({ name: r.name, price: r.price, available: r.available })))
      setExisting({ photos: h.photos, ids: h.photo_ids })
    }).catch((e) => setError(e.message))
  }, [editing, id])

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const toggleAmenity = (a) => setF({ ...f, amenities: f.amenities.includes(a) ? f.amenities.filter((x) => x !== a) : [...f.amenities, a] })
  const room = MAX_PHOTOS - existing.photos.length - files.length

  const setRoom = (i, patch) => setRooms(rooms.map((r, j) => (j === i ? { ...r, ...patch } : r)))
  const addRoom = () => {
    const free = ROOM_TYPES.find((t) => !rooms.some((r) => r.name === t))
    if (free) setRooms([...rooms, { name: free, price: '', available: true }])
  }

  function pick(e) {
    const chosen = [...e.target.files].slice(0, Math.max(room, 0)).map((file) => ({ file, preview: URL.createObjectURL(file) }))
    setFiles([...files, ...chosen]); e.target.value = ''
  }
  async function removeExisting(i) {
    try {
      const h = await api.del(`/hostels/${id}/photos/${existing.ids[i]}`)
      setExisting({ photos: h.photos, ids: h.photo_ids })
    } catch (err) { notify(err.message) }
  }

  async function submit(e) {
    e.preventDefault()
    setError(''); setBusy(true)
    const body = { ...f, distance_km: +f.distance_km, location: f.location || null,
      description: f.description || null, contact_phone: f.contact_phone || null,
      rooms: rooms.map((r) => ({ name: r.name, price: +r.price, available: r.available })) }
    try {
      const saved = editing ? await api.put(`/hostels/${id}`, body) : await api.post('/hostels', body)
      for (const { file } of files) await api.upload(`/hostels/${saved.id}/photos`, file)
      notify(editing ? 'Changes saved ✅' : 'Listing published 🎉')
      nav('/owner')
    } catch (err) { setError(err.message); setBusy(false) }
  }
  async function remove() {
    if (!window.confirm('Delete this listing permanently?')) return
    try { await api.del(`/hostels/${id}`); notify('Listing deleted'); nav('/owner') } catch (err) { setError(err.message) }
  }

  return (<>
    <Hero back="My hostels" backTo="/owner" brand="🔑 OWNER DASHBOARD" title={editing ? 'Edit listing' : 'Add a hostel listing'}
      sub={editing ? 'Changes show to students instantly.' : 'Students will see it right away.'} />
    <form className="wrap form-narrow" onSubmit={submit}>
      <label style={{ marginTop: 0 }}>Hostel name</label>
      <input type="text" required minLength={2} value={f.name} onChange={set('name')} placeholder="e.g. Roysambu Heights" />
      <div className="grid2">
        <div><label>Distance from USIU (km)</label><input type="number" required min="0" step="0.1" value={f.distance_km} onChange={set('distance_km')} placeholder="0.8" /></div>
        <div><label>Area</label><input type="text" value={f.location} onChange={set('location')} placeholder="e.g. Roysambu" /></div>
      </div>
      <label>Contact phone</label>
      <input type="text" value={f.contact_phone} onChange={set('contact_phone')} placeholder="07…" />

      <label>Room types &amp; prices <span className="muted">(KES per person / month)</span></label>
      {rooms.map((r, i) => (
        <div className="roomrow" key={i}>
          <select value={r.name} onChange={(e) => setRoom(i, { name: e.target.value })}>
            {ROOM_TYPES.map((t) => <option key={t} value={t} disabled={rooms.some((x, j) => j !== i && x.name === t)}>{t}</option>)}
          </select>
          <input type="number" required min="1" value={r.price} onChange={(e) => setRoom(i, { price: e.target.value })} placeholder="e.g. 9000" />
          <button type="button" className={`chip ${r.available ? 'on' : ''}`} onClick={() => setRoom(i, { available: !r.available })}>{r.available ? 'Open' : 'Full'}</button>
          {rooms.length > 1 ? <button type="button" className="link" aria-label="Remove room type" onClick={() => setRooms(rooms.filter((_, j) => j !== i))}>✕</button> : <span />}
        </div>
      ))}
      {rooms.length < ROOM_TYPES.length && <button type="button" className="btn ghost" style={{ marginTop: 4 }} onClick={addRoom}>+ Add another room type</button>}

      <label>Amenities</label>
      <AmenityChips items={AMENITIES} selected={f.amenities} onToggle={toggleAmenity} />
      <label>Description (optional)</label>
      <textarea rows={3} value={f.description} onChange={set('description')} placeholder="Water schedule, house rules, what is nearby…" />

      <label>Photos ({existing.photos.length + files.length} of {MAX_PHOTOS})</label>
      <div className="thumbs">
        {room > 0 && <div className="upload" onClick={() => fileInput.current.click()}>📷</div>}
        {existing.photos.map((u, i) => (
          <div className="thumb" key={u} style={{ backgroundImage: `url(${fileUrl(u)})` }}><b onClick={() => removeExisting(i)}>✕</b></div>
        ))}
        {files.map((p, i) => (
          <div className="thumb" key={p.preview} style={{ backgroundImage: `url(${p.preview})` }}>
            <b onClick={() => setFiles(files.filter((_, j) => j !== i))}>✕</b>
          </div>
        ))}
      </div>
      <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={pick} />
      <div className="muted" style={{ marginTop: 6 }}>JPEG, PNG or WebP, up to 5 MB each.</div>

      {error && <div className="error">{error}</div>}
      <button className="btn" disabled={busy}>{busy ? 'Saving…' : editing ? '💾 Save changes' : '🚀 Publish listing'}</button>
      {editing && <button type="button" className="btn danger" onClick={remove}>🗑 Delete listing</button>}
    </form>
  </>)
}
