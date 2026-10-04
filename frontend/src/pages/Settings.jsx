import React, { useEffect, useState } from 'react'
import { api, errMsg } from '../api'
import { Panel } from '../components/ui'

export default function Settings() {
  const [s, setS] = useState(null)
  const [msg, setMsg] = useState('')
  useEffect(() => { api.get('/settings').then((r) => setS(r.data)) }, [])
  if (!s) return null
  const save = async () => { try { const r = await api.post('/settings', { threshold_scale: s.threshold_scale, smoothing: s.smoothing }); setS(r.data); setMsg('Saved') } catch (e) { setMsg(errMsg(e)) } }
  return (
    <Panel title="Engine settings" className="max-w-2xl">
      <div className="label mb-1">Detection threshold scale: {Number(s.threshold_scale).toFixed(2)}x</div>
      <input type="range" min="0.25" max="3" step="0.05" value={s.threshold_scale} onChange={(e) => setS({ ...s, threshold_scale: Number(e.target.value) })} />
      <div className="text-xs mb-4" style={{ color: 'var(--muted)' }}>Multiplies the calibrated per-class thresholds. Below 1 = more sensitive (more false alarms); above 1 = stricter.</div>
      <div className="label mb-1">Probability smoothing: {Number(s.smoothing).toFixed(2)}</div>
      <input type="range" min="0" max="0.9" step="0.05" value={s.smoothing} onChange={(e) => setS({ ...s, smoothing: Number(e.target.value) })} />
      <div className="mt-5 flex items-center gap-4"><button className="btn btn-primary" onClick={save}>Apply</button><span className="text-sm">{msg}</span></div>
      <div className="mt-6 text-sm" style={{ color: 'var(--muted)' }}>Model: <b className="text-slate-200">{s.model}</b><br />Window: {s.window} polls<br />Classes: {s.classes.join(', ')}<br />Calibrated thresholds: {Object.entries(s.thresholds || {}).map(([k, v]) => `${k} ${v.toFixed(2)}`).join(' · ')}</div>
    </Panel>
  )
}
