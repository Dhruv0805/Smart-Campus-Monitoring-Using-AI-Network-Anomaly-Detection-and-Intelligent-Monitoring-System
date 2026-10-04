import React from 'react'
import { useMonitor } from '../MonitorContext'
import { Loading, Panel, RiskBadge } from '../components/ui'
import { LEVEL_COLOR, fmt } from '../api'

export default function Network() {
  const { state } = useMonitor()
  if (!state) return <Loading />
  const cx = 350, cy = 230, R = 170
  const nodes = state.zones.map((z, i) => { const a = (2 * Math.PI * i) / state.zones.length - Math.PI / 2; return { ...z, x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) } })
  return (
    <div className="space-y-5">
      <Panel title="Campus topology">
        <svg viewBox="0 0 700 460" className="w-full" style={{ maxHeight: 460 }}>
          {nodes.map((n) => { const hit = n.latest?.confirmed, c = LEVEL_COLOR[n.latest?.risk?.level || 'NORMAL']
            return (<g key={n.id}>
              <line x1={cx} y1={cy} x2={n.x} y2={n.y} stroke={hit ? c : '#334170'} strokeWidth={hit ? 3 : 2} strokeDasharray={hit ? '6 4' : ''} />
              <circle cx={n.x} cy={n.y} r={34} fill={c + '22'} stroke={c} strokeWidth={3} className={hit ? 'pulse' : ''} />
              <text x={n.x} y={n.y + 4} textAnchor="middle" fill="#e5e9f7" fontSize="11" fontWeight="600">{n.gateway.replace('GW-', '')}</text>
              <text x={n.x} y={n.y + 58} textAnchor="middle" fill="#8d9ac7" fontSize="12">{n.name}</text>
            </g>) })}
          <circle cx={cx} cy={cy} r={44} fill="#4f46e5" opacity=".85" /><text x={cx} y={cy + 4} textAnchor="middle" fill="white" fontWeight="700" fontSize="13">CAMPUS CORE</text>
        </svg>
      </Panel>
      <Panel title="Zone telemetry (latest poll)">
        <table><thead><tr><th>Zone</th><th>Gateway</th><th>Packets/int</th><th>Bytes/int</th><th>TCP</th><th>UDP</th><th>ICMP</th><th>AI verdict</th><th>Risk</th></tr></thead>
          <tbody>{state.zones.map((z) => { const l = z.latest, m = l?.metrics || {}
            return (<tr key={z.id}><td>{z.name}</td><td>{z.gateway}</td><td>{fmt(m.packet_rate)}</td><td>{fmt(m.byte_rate)}</td><td>{fmt(m.tcp_rate)}</td><td>{fmt(m.udp_rate)}</td><td>{fmt(m.icmp_rate)}</td>
              <td>{l?.confirmed ? l.prediction : 'normal'}</td><td><RiskBadge level={l?.risk?.level || 'NORMAL'} /></td></tr>) })}</tbody></table>
      </Panel>
    </div>
  )
}
