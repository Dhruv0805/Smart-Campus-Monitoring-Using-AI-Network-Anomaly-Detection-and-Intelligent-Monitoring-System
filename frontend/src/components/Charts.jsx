import React from 'react'
import { Area, CartesianGrid, ComposedChart, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis, Line } from 'recharts'
import { LEVEL_COLOR, fmt } from '../api'

const Marker = ({ cx, cy, payload }) => {
  if (cx == null || cy == null) return null
  const c = LEVEL_COLOR[payload.level] || '#ef4444'
  return (<g><circle cx={cx} cy={cy} r={9} fill={c} fillOpacity={0.25} /><path d={`M${cx - 5},${cy - 5}L${cx + 5},${cy + 5}M${cx + 5},${cy - 5}L${cx - 5},${cy + 5}`} stroke={c} strokeWidth={2.5} /></g>)
}

const Tip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (<div className="card p-2 text-xs"><div>t = {p.t}s</div><div>packets: {fmt(p.packet_rate)}</div>
    <div>risk: {p.risk} ({p.level})</div>{p.confirmed && <div style={{ color: LEVEL_COLOR[p.level] }}>AI: {p.prediction} ({Math.round(p.confidence * 100)}%)</div>}</div>)
}

/** Packet-rate line with AI detection markers placed at the detection timestamp. */
export function TrafficChart({ data, height = 320 }) {
  const rows = (data || []).map((p) => ({ ...p, marker: p.confirmed ? p.packet_rate : null }))
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={rows} margin={{ left: 0, right: 10, top: 10 }}>
        <defs><linearGradient id="pk" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#38bdf8" stopOpacity={0.45} /><stop offset="95%" stopColor="#38bdf8" stopOpacity={0} /></linearGradient></defs>
        <CartesianGrid stroke="#27345f" strokeDasharray="3 3" />
        <XAxis dataKey="t" stroke="#8d9ac7" tick={{ fontSize: 11 }} />
        <YAxis stroke="#8d9ac7" tickFormatter={fmt} tick={{ fontSize: 11 }} width={50} />
        <Tooltip content={<Tip />} />
        <Area type="monotone" dataKey="packet_rate" stroke="#38bdf8" strokeWidth={2} fill="url(#pk)" isAnimationActive={false} />
        <Scatter dataKey="marker" shape={<Marker />} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

export function RiskChart({ data, height = 220 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data || []} margin={{ left: 0, right: 10, top: 10 }}>
        <CartesianGrid stroke="#27345f" strokeDasharray="3 3" />
        <XAxis dataKey="t" stroke="#8d9ac7" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 100]} stroke="#8d9ac7" tick={{ fontSize: 11 }} width={34} />
        <Tooltip contentStyle={{ background: '#111a3b', border: '1px solid #27345f' }} />
        <Area type="monotone" dataKey="risk" stroke="#a78bfa" strokeWidth={2} fill="#a78bfa22" isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

export { Line }
