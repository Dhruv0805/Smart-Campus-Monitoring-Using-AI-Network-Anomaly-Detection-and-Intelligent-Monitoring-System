import React from 'react'
import { NavLink } from 'react-router-dom'
import { useMonitor } from '../MonitorContext'
import { LEVEL_COLOR } from '../api'

const NAV = [['/', 'Dashboard', '▦'], ['/network', 'Network', '⌬'], ['/anomalies', 'Anomalies', '⚠'], ['/devices', 'Devices', '▤'],
  ['/simulation', 'Simulation', '⚙'], ['/analytics', 'Analytics', '◔'], ['/settings', 'Settings', '☰']]

export default function Layout({ children }) {
  const { state, online } = useMonitor()
  const risk = state?.overall_risk || 'NORMAL'
  return (
    <div className="flex h-full">
      <aside className="w-56 shrink-0 p-4 hidden md:flex flex-col gap-1" style={{ background: '#0a0f20', borderRight: '1px solid #1d2748' }}>
        <div className="mb-5"><div className="text-lg font-extrabold tracking-wide">🛰️ SMART CAMPUS</div><div className="label">AI network monitor</div></div>
        {NAV.map(([to, name, icon]) => (
          <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) =>
            `px-3 py-2.5 rounded-xl flex gap-3 items-center text-sm font-medium transition ${isActive ? 'text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
            style={({ isActive }) => (isActive ? { background: 'linear-gradient(90deg,#4f46e5aa,#2563eb66)' } : {})}>
            <span className="w-5 text-center">{icon}</span>{name}
          </NavLink>))}
      </aside>
      <main className="flex-1 overflow-y-auto">
        <header className="sticky top-0 z-10 flex items-center justify-between px-6 py-3" style={{ background: 'rgba(11,16,32,.85)', backdropFilter: 'blur(8px)', borderBottom: '1px solid #1d2748' }}>
          <div className="font-semibold">Smart Campus AI Monitor</div>
          <div className="flex items-center gap-4 text-sm">
            <span>Risk <b style={{ color: LEVEL_COLOR[risk] }}>{risk}</b></span>
            <span className="flex items-center gap-2" style={{ color: online ? '#22c55e' : '#ef4444' }}>
              <span className={`w-2.5 h-2.5 rounded-full ${online ? 'pulse' : ''}`} style={{ background: online ? '#22c55e' : '#ef4444' }} />{online ? (state?.system === 'PAUSED' ? 'PAUSED' : 'LIVE') : 'API OFFLINE'}
            </span>
          </div>
        </header>
        <div className="p-6 max-w-[1500px] mx-auto">{children}</div>
        <nav className="md:hidden flex overflow-x-auto gap-1 p-2 sticky bottom-0" style={{ background: '#0a0f20' }}>
          {NAV.map(([to, name]) => <NavLink key={to} to={to} end={to === '/'} className="px-3 py-2 text-xs rounded-lg text-slate-300 whitespace-nowrap">{name}</NavLink>)}
        </nav>
      </main>
    </div>
  )
}
