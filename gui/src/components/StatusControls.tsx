import { useEffect, useState } from 'react'
import { getStatus, setStatus, type JarvisStatus } from '@/api/api'
import {useJarvisStore} from "@/store/store.ts";

type Pending = 'online' | 'listening' | 'speaking' | null

export default function StatusControls() {
  const [status, setLocal] = useState<JarvisStatus | null>(null)
  const [pending, setPending] = useState<Pending>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    getStatus().then(setLocal).catch(e => setErr(String(e)))
  }, [])

  const sync = async (patch: Partial<JarvisStatus>, key: Pending) => {
  if (!status) return
  setPending(key)
  setErr(null)

  try {
    const res = await setStatus(patch)   // API виклик
    setLocal(res)                        // локальний стейт
    useJarvisStore.setState({ status: res }) // Zustand глобальний
  } catch (e: any) {
    setErr(e.message || String(e))
  } finally {
    setPending(null)
  }
}

  if (!status) {
    return <div style={{opacity:.7}}>Loading status…</div>
  }

  const disOnline = pending !== null
  const disListening = pending !== null || !status.online
  const disSpeaking = pending !== null || !status.online || !status.listening

  return (
    <div style={{display:'grid', gap:12, maxWidth:520}}>
      {err && <div style={{color:'#f87171', fontSize:13}}>{err}</div>}

      <Row
        label="Online"
        value={status.online}
        onToggle={() => sync({ online: !status.online, ...(status.online ? { speaking:false, listening:false } : {}) }, 'online')}
        disabled={disOnline}
      />

      <Row
        label="Listening"
        hint={!status.online ? 'Enable Online first' : undefined}
        value={status.listening}
        onToggle={() => sync({ listening: !status.listening }, 'listening')}
        disabled={disListening}
      />

      <Row
        label="Speaking"
        hint={!status.online ? 'Enable Online first' : !status.listening ? 'Enable Listening first' : undefined}
        value={status.speaking}
        onToggle={() => sync({ speaking: !status.speaking }, 'speaking')}
        disabled={disSpeaking}
      />
    </div>
  )
}

function Row({
  label, value, onToggle, disabled, hint,
}: {
  label: string
  value: boolean
  onToggle: () => void
  disabled?: boolean
  hint?: string
}) {
  return (
    <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:12, border:'1px solid #2a2a2a', borderRadius:12, padding:12}}>
      <div>
        <div style={{fontWeight:600}}>{label}</div>
        {hint && <div style={{opacity:.7, fontSize:12}}>{hint}</div>}
      </div>
      <button
        onClick={onToggle}
        disabled={!!disabled}
        style={{
          minWidth:96,
          padding:'8px 12px',
          border:'1px solid #3a3a3a',
          borderRadius:999,
          background: disabled ? '#333' : value ? '#16a34a' : '#ef4444',
          color: 'white',
          cursor: disabled ? 'not-allowed' : 'pointer',
          fontWeight:700,
        }}
        aria-pressed={value}
      >
        {value ? 'ON' : 'OFF'}
      </button>
    </div>
  )
}
