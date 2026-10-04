import React from 'react'
import { LEVEL_COLOR } from '../api'

export const Kpi = ({ label, value, color, sub }) => (
  <div className="card p-4">
    <div className="label">{label}</div>
    <div className="text-3xl font-bold mt-1" style={{ color: color || '#e5e9f7' }}>{value}</div>
    {sub && <div className="text-xs mt-1" style={{ color: 'var(--muted)' }}>{sub}</div>}
  </div>
)

export const RiskBadge = ({ level }) => (
  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
    style={{ background: (LEVEL_COLOR[level] || '#64748b') + '26', color: LEVEL_COLOR[level] || '#94a3b8', border: `1px solid ${(LEVEL_COLOR[level] || '#64748b')}55` }}>{level}</span>
)

export const Panel = ({ title, right, children, className = '' }) => (
  <div className={`card p-4 ${className}`}>
    <div className="flex items-center justify-between mb-3"><h3 className="font-semibold">{title}</h3>{right}</div>
    {children}
  </div>
)

export const Loading = () => <div className="p-10 text-center" style={{ color: 'var(--muted)' }}>Connecting to monitoring API…</div>
