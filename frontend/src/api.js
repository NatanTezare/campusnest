// Thin fetch wrapper: adds the JWT, parses errors from FastAPI into readable messages.
const BASE = import.meta.env.VITE_API_URL || ''

export const getToken = () => localStorage.getItem('cn_token')

async function request(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const res = await fetch(`${BASE}/api${path}`, { method, headers, body: payload })
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const d = data?.detail
    const msg = Array.isArray(d) ? d.map((x) => x.msg).join(', ') : d || res.statusText
    const err = new Error(msg)
    err.status = res.status
    throw err
  }
  return data
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: 'POST', body }),
  put: (p, body) => request(p, { method: 'PUT', body }),
  del: (p) => request(p, { method: 'DELETE' }),
  upload: (p, file) => {
    const f = new FormData()
    f.append('file', file)
    return request(p, { method: 'POST', form: f })
  },
}

export const fileUrl = (u) => (u ? `${BASE}${u}` : null)
export const AMENITIES = ['WiFi', 'Water backup', 'Security', 'Kitchen', 'Study desk', 'Laundry']
export const ROOM_TYPES = ['Single room', 'Twin sharing', 'Triple sharing', 'Bedsitter', 'Studio']
export const kes = (n) => 'KES ' + Number(n).toLocaleString()
