import React, { useEffect, useState } from 'react'
import { api, errMsg } from '../api'
import { useMonitor } from '../MonitorContext'
import { Loading, Panel } from '../components/ui'

export default function Simulation() {
  const { state } = useMonitor()
  const [types, setTypes] = useState({})
  const [attack, setAttack] = useState('tcp-syn')
  const [zone, setZone] = useState('')
  const [intensity, setIntensity] = useState(0.8)
  const [duration, setDuration] = useState(15)
  const [msg, setMsg] = useState(null)
  useEffect(() => { api.get('/attack-types').then((r) => setTypes(r.data.types)) }, [])
  if (!state) return <Loading />
  const cfg = state.config
  const act = async (fn, ok) => { try { const r = await fn(); setMsg({ ok: true, text: ok(r.data) }) } catch (e) { setMsg({ ok: false, text: errMsg(e) }) } }
  const setCfg = (patch) => act(() => api.post('/simulation/config', patch), () => 'Configuration updated')
  const toggle = (label, on, patch) => (
    <label className="flex items-center justify-between py-2 cursor-pointer"><span>{label}</span>
      <button className="btn" style={{ minWidth: 70, background: on ? '#14532d' : '#18224a' }} onClick={() => setCfg(patch(!on))}>{on ? 'ON' : 'OFF'}</button></label>)
  return (
    <div className="grid lg:grid-cols-2 gap-5">
      <Panel title="Simulation control">
        {toggle('Simulation', cfg.running, (v) => ({ running: v }))}
        {toggle('Random anomalies', cfg.random_anomalies, (v) => ({ random_anomalies: v }))}
        <div className="mt-3"><div className="label mb-1">Mean seconds between random anomalies: {cfg.random_mean_gap_s}</div>
          <input type="range" min="10" max="300" step="5" value={cfg.random_mean_gap_s} onChange={(e) => setCfg({ random_mean_gap_s: Number(e.target.value) })} /></div>
        <div className="mt-6 flex gap-3">
          <button className="btn" onClick={() => act(() => api.post('/simulation/reset'), () => 'Monitor reset')}>Reset monitor</button>
        </div>
        <h4 className="font-semibold mt-6 mb-2">Active incidents</h4>
        <table><thead><tr><th>Type</th><th>Zone</th><th>Source</th><th>Intensity</th><th>Left</th></tr></thead>
          <tbody>{state.active_incidents.map((i) => <tr key={i.id}><td>{i.type}</td><td>{i.zone}</td><td>{i.source}</td><td>{i.intensity.toFixed(2)}</td><td>{Math.max(0, Math.round(i.end - state.sim_time))}s</td></tr>)}
            {!state.active_incidents.length && <tr><td colSpan="5" style={{ color: 'var(--muted)' }}>None - traffic is normal.</td></tr>}</tbody></table>
      </Panel>
      <Panel title="Manual anomaly injection">
        <div className="label mb-1">Attack type</div>
        <select value={attack} onChange={(e) => setAttack(e.target.value)}>{Object.entries(types).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select>
        <div className="text-xs mt-1" style={{ color: 'var(--muted)' }}>{types[attack]?.desc}</div>
        <div className="label mt-4 mb-1">Target zone</div>
        <select value={zone} onChange={(e) => setZone(e.target.value)}><option value="">Automatic (typical target)</option>{state.zones.map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}</select>
        <div className="label mt-4 mb-1">Intensity: {intensity.toFixed(2)}</div>
        <input type="range" min="0.1" max="1" step="0.05" value={intensity} onChange={(e) => setIntensity(Number(e.target.value))} />
        <div className="label mt-4 mb-1">Duration: {duration} s</div>
        <input type="range" min="3" max="120" step="1" value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
        <div className="flex gap-3 mt-6">
          <button className="btn btn-primary flex-1" onClick={() => act(() => api.post('/simulation/inject', { attack, zone: zone || undefined, intensity, duration }), (d) => `Injected ${d.type} into ${d.zone} for ${duration}s`)}>START ANOMALY</button>
          <button className="btn btn-danger" onClick={() => act(() => api.post('/simulation/stop', {}), (d) => `Stopped ${d.stopped} incident(s)`)}>STOP ALL</button>
        </div>
        {msg && <div className="mt-3 text-sm" style={{ color: msg.ok ? '#22c55e' : '#f87171' }}>{msg.text}</div>}
        <div className="text-xs mt-4" style={{ color: 'var(--muted)' }}>Low intensities blend toward normal traffic, so weak attacks may evade detection - that is realistic behaviour, not a bug.</div>
      </Panel>
    </div>
  )
}
