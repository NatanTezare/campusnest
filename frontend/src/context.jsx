import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api } from './api'

const Ctx = createContext(null)
export const useApp = () => useContext(Ctx)

const load = (k, fallback) => {
  try { return JSON.parse(localStorage.getItem(k)) ?? fallback } catch { return fallback }
}

export function AppProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)
  const [toast, setToast] = useState(null)
  const [compare, setCompare] = useState(() => load('cn_compare', []))
  const [prefs, setPrefs] = useState(() => ({ budget: 15000, max_distance_km: 2, amenities: ['WiFi', 'Security'], room_type: 'Any', ...load('cn_prefs', {}) }))
  const [scores, setScores] = useState({}) // hostel id -> match %, from the last recommendation

  useEffect(() => { localStorage.setItem('cn_compare', JSON.stringify(compare)) }, [compare])
  useEffect(() => { localStorage.setItem('cn_prefs', JSON.stringify(prefs)) }, [prefs])

  useEffect(() => {
    if (!localStorage.getItem('cn_token')) { setReady(true); return }
    api.get('/auth/me').then(setUser).catch(() => localStorage.removeItem('cn_token')).finally(() => setReady(true))
  }, [])

  const notify = useCallback((msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 2400)
  }, [])

  const authenticate = useCallback(async (path, body) => {
    const res = await api.post(path, body)
    localStorage.setItem('cn_token', res.access_token)
    setUser(res.user)
    return res.user
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('cn_token')
    setUser(null)
    setCompare([])
  }, [])

  const toggleCompare = useCallback((id) => {
    setCompare((c) => {
      if (c.includes(id)) return c.filter((x) => x !== id)
      if (c.length >= 3) { notify('You can compare up to 3 hostels'); return c }
      return [...c, id]
    })
  }, [notify])

  const value = useMemo(() => ({
    user, ready, toast, notify, authenticate, logout,
    compare, setCompare, toggleCompare, prefs, setPrefs, scores, setScores,
  }), [user, ready, toast, notify, authenticate, logout, compare, toggleCompare, prefs, scores])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
