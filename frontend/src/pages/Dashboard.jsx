import React, { useState } from 'react'
import { useMonitor } from '../MonitorContext'
import { Kpi, Loading, Panel, RiskBadge } from '../components/ui'
import { RiskChart, TrafficChart } from '../components/Charts'
import { LEVEL_COLOR, fmt } from '../api'

export default function Dashboard() {
  const { state, series, events } = useMonitor()
  const [zone, setZone] = useState('services')
  if (!state) return <Loading />
  const z = state.zones.find((x) => x.id === zone)
  const data = series[zone] || []
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="Network status" value={state.system === 'ONLINE' ? '● ONLINE' : '❚❚ PAUSED'} color={state.system === 'ONLINE' ? '#22c55e' : '#eab308'} sub={`sim time ${Math.round(state.sim_time)}s`} />
        <Kpi label="Active anomalies" value={String(state.anomalies_now).padStart(2, '0')} color={state.anomalies_now ? '#ef4444' : undefined} sub={`${state.active_incidents.length} injected incident(s) running`} />
        <Kpi label="Overall risk" value={state.overall_risk} color={LEVEL_COLOR[state.overall_risk]} />
        <Kpi label="Alerts raised" value={state.alerts_total} sub={`false-alarm ticks ${(state.stats.false_alarm_tick_rate * 100).toFixed(1)}%`} />
      </div>

      <Panel title={`Real-time packet rate - ${z?.name}`} right={
        <select style={{ width: 200 }} value={zone} onChange={(e) => setZone(e.target.value)}>{state.zones.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>}>
        <TrafficChart data={data} />
        <div className="text-xs mt-1" style={{ color: 'var(--muted)' }}>✕ markers = AI-confirmed anomaly at its detection timestamp, coloured by risk level.</div>
      </Panel>

      <div className="grid lg:grid-cols-3 gap-5">
        <Panel title="Risk score" className="lg:col-span-1"><RiskChart data={data} /></Panel>
        <Panel title="Network zones" className="lg:col-span-2">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {state.zones.map((x) => {
              const l = x.latest, lvl = l?.risk?.level || 'NORMAL'
              return (
                <button key={x.id} onClick={() => setZone(x.id)} className="card p-3 text-left" style={{ borderColor: x.id === zone ? '#6366f1' : undefined }}>
                  <div className="label">{x.name}</div>
                  <div className="flex items-center justify-between mt-1"><RiskBadge level={lvl} /><span className="text-xs">{fmt(l?.metrics?.packet_rate)} pkt</span></div>
                  <div className="text-xs mt-1" style={{ color: l?.confirmed ? LEVEL_COLOR[lvl] : 'var(--muted)' }}>{l?.confirmed ? `⚠ ${l.prediction}` : 'normal traffic'}</div>
                </button>)
            })}
          </div>
        </Panel>
      </div>

      <Panel title="Recent anomalies">
        <table><thead><tr><th>Time</th><th>Zone</th><th>Attack</th><th>Confidence</th><th>Risk</th></tr></thead>
          <tbody>{events.slice(0, 6).map((e) => (
            <tr key={e.id}><td>{Math.round(e.timestamp)}s</td><td>{state.zones.find((x) => x.id === e.zone)?.name}</td><td>{e.attack_label}</td>
              <td>{Math.round(e.confidence * 100)}%</td><td><RiskBadge level={e.risk_level} /></td></tr>))}
            {!events.length && <tr><td colSpan="5" style={{ color: 'var(--muted)' }}>No anomalies yet - open the Simulation page and press START ANOMALY.</td></tr>}</tbody></table>
      </Panel>
    </div>
  )
}
