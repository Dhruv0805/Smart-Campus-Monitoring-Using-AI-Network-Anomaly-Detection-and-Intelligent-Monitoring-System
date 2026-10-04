import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useMonitor } from '../MonitorContext'
import { Panel, RiskBadge } from '../components/ui'

export default function Devices() {
  const { state } = useMonitor()
  const [devs, setDevs] = useState([])
  const [zone, setZone] = useState('')
  useEffect(() => { const load = () => api.get('/devices').then((r) => setDevs(r.data)).catch(() => {}); load(); const id = setInterval(load, 2000); return () => clearInterval(id) }, [])
  const rows = devs.filter((d) => !zone || d.zone === zone)
  return (
    <Panel title={`Campus & IoT devices (${rows.length})`} right={
      <select style={{ width: 200 }} value={zone} onChange={(e) => setZone(e.target.value)}><option value="">All zones</option>{(state?.zones || []).map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}</select>}>
      <table><thead><tr><th>Device</th><th>Type</th><th>Zone</th><th>Address</th><th>Services</th><th>Status</th><th>Risk</th></tr></thead>
        <tbody>{rows.map((d) => (
          <tr key={d.id}><td>{d.name}</td><td>{d.type}</td><td>{state?.zones.find((z) => z.id === d.zone)?.name}</td><td>{d.ip}</td><td>{d.services.join(', ')}</td>
            <td style={{ color: d.status === 'healthy' ? '#22c55e' : '#ef4444' }}>{d.status}{d.attack ? ` (${d.attack})` : ''}</td><td><RiskBadge level={d.risk_level} /></td></tr>))}</tbody></table>
    </Panel>
  )
}
