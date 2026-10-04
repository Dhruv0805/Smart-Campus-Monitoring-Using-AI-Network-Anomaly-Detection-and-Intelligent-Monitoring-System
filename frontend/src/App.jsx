import React from 'react'
import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { MonitorProvider } from './MonitorContext'
import Dashboard from './pages/Dashboard'
import Network from './pages/Network'
import Anomalies from './pages/Anomalies'
import Devices from './pages/Devices'
import Simulation from './pages/Simulation'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'

export default function App() {
  return (
    <MonitorProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/network" element={<Network />} />
          <Route path="/anomalies" element={<Anomalies />} />
          <Route path="/devices" element={<Devices />} />
          <Route path="/simulation" element={<Simulation />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </MonitorProvider>
  )
}
