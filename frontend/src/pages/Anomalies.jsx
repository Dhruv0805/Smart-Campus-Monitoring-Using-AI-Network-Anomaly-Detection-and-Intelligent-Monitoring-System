import React, { useState } from 'react'
import { useMonitor } from '../MonitorContext'
import { Kpi, Loading, Panel, RiskBadge } from '../components/ui'

export default function Anomalies() {
  const { state, events } = useMonitor()
  const [filter, setFilter] = useState('')
  if (!state) return <Loading />
  const types = [...new Set(events.map((e) => e.attack))]
  const rows = events.filter((e) => !filter || e.attack === filter)
  const s = state.stats
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="Alerts (total)" value={s.alerts} />
        <Kpi label="Per-poll accuracy vs ground truth" value={`${(s.tick_accuracy * 100).toFixed(1)}%`} />
        <Kpi label="False-alarm polls" value={`${(s.false_alarm_tick_rate * 100).toFixed(1)}%`} />
        <Kpi label="Missed-anomaly polls" value={s.missed_ticks} />
      </div>
      <Panel title="Anomaly history" right={<select style={{ width: 180 }} value={filter} onChange={(e) => setFilter(e.target.value)}><option value="">All types</option>{types.map((t) => <option key={t}>{t}</option>)}</select>}>
        <table><thead><tr><th>#</th><th>Sim time</th><th>Zone</th><th>Device</th><th>Detected</th><th>Ground truth</th><th>Confidence</th><th>Score</th><th>Risk</th></tr></thead>
          <tbody>{rows.map((e) => (
            <tr key={e.id}><td>{e.id}</td><td>{Math.round(e.timestamp)}s</td><td>{state.zones.find((z) => z.id === e.zone)?.name}</td><td>{e.device}</td><td>{e.attack_label}</td>
              <td style={{ color: e.correct ? '#22c55e' : '#f97316' }}>{e.truth}</td><td>{Math.round(e.confidence * 100)}%</td><td>{e.risk_score}</td><td><RiskBadge level={e.risk_level} /></td></tr>))}
            {!rows.length && <tr><td colSpan="9" style={{ color: 'var(--muted)' }}>Nothing recorded yet.</td></tr>}</tbody></table>
      </Panel>
    </div>
  )
}
