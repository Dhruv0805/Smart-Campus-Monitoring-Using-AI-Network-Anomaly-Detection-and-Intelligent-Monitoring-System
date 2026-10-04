import React, { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { Kpi, Loading, Panel } from '../components/ui'

const num = (v) => Number(v)
export default function Analytics() {
  const [a, setA] = useState(null)
  useEffect(() => { api.get('/analytics').then((r) => setA(r.data)) }, [])
  if (!a) return <Loading />
  const ds1 = a.comparison.filter((r) => r.dataset === 'ds1' && !r.experiment.includes('infogain20')).map((r) => ({ name: r.experiment.replace(' [delta+window, 105 feat]', '').replace(' + per-class thresholds (FAR budget 10%)', ' +thr').replace('DIAGNOSTIC ', 'DIAG ').replace('DEPLOY ', 'DEPLOY ').replace(' [all34]', '').replace('IMPROVED ', 'IMP ').replace('BASELINE ', 'BASE '), protocol: r.protocol, macro_f1: num(r.macro_f1), accuracy: num(r.accuracy), key: r.experiment + r.protocol }))
  const cal = a.calibration
  const cm = a.confusion
  const max = cm ? Math.max(...cm.matrix.flat()) : 1
  const sweep = cal ? cal.sweep.map((r) => ({ thr: r.scale + 'x', FAR: +(r.false_alarm_rate * 100).toFixed(1), Recall: +(r.binary_anomaly_recall * 100).toFixed(1) })) : []
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="Deployed model" value={(a.calibration?.model || '-')} />
        <Kpi label="Honest macro-F1" value={cal ? (cal.metrics_at_thresholds.macro_f1 * 100).toFixed(1) + '%' : '-'} sub="blocked CV + embargo" />
        <Kpi label="Anomaly recall" value={cal ? (cal.metrics_at_thresholds.binary_anomaly_recall * 100).toFixed(1) + '%' : '-'} sub="normal vs attack" />
        <Kpi label="False-alarm rate" value={cal ? (cal.metrics_at_thresholds.false_alarm_rate * 100).toFixed(1) + '%' : '-'} sub="calibrated per-class thresholds" />
      </div>
      <Panel title="Dataset 1: Paper-1 baseline vs improved pipeline (accuracy / macro-F1)">
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={ds1} margin={{ bottom: 90 }}><CartesianGrid stroke="#27345f" strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-35} textAnchor="end" interval={0} tick={{ fontSize: 10, fill: '#8d9ac7' }} /><YAxis domain={[0, 1]} stroke="#8d9ac7" />
            <Tooltip contentStyle={{ background: '#111a3b', border: '1px solid #27345f' }} /><Legend verticalAlign="top" />
            <Bar dataKey="accuracy" fill="#a78bfa" /><Bar dataKey="macro_f1" fill="#38bdf8" /></BarChart>
        </ResponsiveContainer>
        <div className="text-xs" style={{ color: 'var(--muted)' }}>Baselines scored with the paper's random 10-fold are near-perfect because neighbouring rows of a cumulative counter are almost identical (leakage); the same models under blocked CV and the improved delta features give the honest picture.</div>
      </Panel>
      <div className="grid lg:grid-cols-2 gap-5">
        {cm && <Panel title="Confusion matrix (deployed model, honest CV)">
          <div className="overflow-x-auto"><table style={{ fontSize: 11 }}><thead><tr><th></th>{cm.labels.map((l) => <th key={l}>{l}</th>)}</tr></thead>
            <tbody>{cm.matrix.map((row, i) => <tr key={i}><td className="label">{cm.labels[i]}</td>{row.map((v, j) => <td key={j} style={{ background: `rgba(56,189,248,${(v / max) * 0.85})`, textAlign: 'center' }}>{v}</td>)}</tr>)}</tbody></table></div></Panel>}
        {cal && <Panel title="Sensitivity sweep (threshold scale: false alarms vs attack recall)">
          <ResponsiveContainer width="100%" height={300}><LineChart data={sweep}><CartesianGrid stroke="#27345f" strokeDasharray="3 3" />
            <XAxis dataKey="thr" stroke="#8d9ac7" /><YAxis stroke="#8d9ac7" unit="%" /><Tooltip contentStyle={{ background: '#111a3b', border: '1px solid #27345f' }} /><Legend />
            <Line dataKey="FAR" stroke="#f97316" dot={false} /><Line dataKey="Recall" stroke="#22c55e" dot={false} /></LineChart></ResponsiveContainer></Panel>}
      </div>
      {a.window_ablation && <Panel title="Window-size ablation (HistGradientBoosting)"><table><thead><tr><th>Window</th><th>Accuracy</th><th>Macro-F1</th><th>Anomaly F1</th></tr></thead>
        <tbody>{a.window_ablation.map((r) => <tr key={r.window}><td>{r.window}</td><td>{r.accuracy}</td><td>{r.macro_f1}</td><td>{r.binary_anomaly_f1}</td></tr>)}</tbody></table></Panel>}
      <Panel title="All experiments"><div className="overflow-x-auto"><table><thead><tr><th>Experiment</th><th>Protocol</th><th>Acc</th><th>Macro-F1</th><th>Anomaly F1</th><th>FAR</th></tr></thead>
        <tbody>{a.comparison.map((r, i) => <tr key={i}><td>{r.experiment}</td><td>{r.protocol}</td><td>{r.accuracy}</td><td>{r.macro_f1}</td><td>{r.binary_anomaly_f1}</td><td>{r.false_alarm_rate}</td></tr>)}</tbody></table></div></Panel>
    </div>
  )
}
