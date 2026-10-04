import axios from 'axios'

export const api = axios.create({ baseURL: '/api', timeout: 8000 })

export const LEVEL_COLOR = { NORMAL: '#22c55e', LOW: '#eab308', MEDIUM: '#f97316', HIGH: '#ef4444', CRITICAL: '#d946ef' }
export const fmt = (n) => (n == null ? '-' : Number(n) >= 1e9 ? (n / 1e9).toFixed(2) + 'G' : Number(n) >= 1e6 ? (n / 1e6).toFixed(2) + 'M' : Number(n) >= 1e3 ? (n / 1e3).toFixed(1) + 'k' : String(Math.round(n)))
export const errMsg = (e) => e?.response?.data?.error || e?.message || 'request failed'
