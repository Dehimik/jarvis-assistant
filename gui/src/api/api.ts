import { api } from './client.js'

export type JarvisStatus = {
  online: boolean
  listening: boolean
  speaking: boolean
  version?: string
}

export async function getStatus(): Promise<JarvisStatus> {
  const { data } = await api.get('/api/status')
  return data
}

export async function setStatus(patch: Partial<JarvisStatus>): Promise<JarvisStatus> {
  const { data } = await api.post('/api/status/toggle', patch)
    return data as JarvisStatus;
}

export type JarvisSettings = {
  stt_device?: string
  tts_voice?: string
  locale?: string
  openai_key?: string | null
}

export async function getSettings(): Promise<JarvisSettings> {
  const { data } = await api.get('/api/settings')
  return data
}

export async function updateSettings(patch: Partial<JarvisSettings>): Promise<JarvisSettings> {
  const { data } = await api.post('/api/settings', patch)
  return data
}

export function connectLogsWS(): WebSocket {
  // Expect FastAPI at ws://127.0.0.1:8000/api/logs/stream
  const ws = new WebSocket('ws://127.0.0.1:8000/api/logs/stream')
  return ws
}