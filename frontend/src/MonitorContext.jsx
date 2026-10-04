import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import { api } from './api'

const Ctx = createContext(null)
export const useMonitor = () => useContext(Ctx)

/** Polls the Flask API once per second and shares the result with every page. */
export function MonitorProvider({ children }) {
  const [state, setState] = useState(null)
  const [series, setSeries] = useState({})
  const [events, setEvents] = useState([])
  const [online, setOnline] = useState(true)
  const busy = useRef(false)

  useEffect(() => {
    let alive = true
    const tick = async () => {
      if (busy.current) return
      busy.current = true
      try {
        const [s, ser, ev] = await Promise.all([api.get('/state'), api.get('/series?limit=150'), api.get('/events?limit=200')])
        if (!alive) return
        setState(s.data); setSeries(ser.data); setEvents(ev.data); setOnline(true)
      } catch { if (alive) setOnline(false) }
      finally { busy.current = false }
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => { alive = false; clearInterval(id) }
  }, [])

  return <Ctx.Provider value={{ state, series, events, online }}>{children}</Ctx.Provider>
}
