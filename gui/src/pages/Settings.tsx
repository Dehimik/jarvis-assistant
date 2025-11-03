import Header from '@/components/Header'
import Card from '@/components/Card'
import { useEffect, useState } from 'react'
import { getSettings, updateSettings, type JarvisSettings } from '@/api/api'
import { useJarvisStore } from '@/store/store'

export default function Settings() {
  const { settings, setSettings } = useJarvisStore()
  const [local, setLocal] = useState<JarvisSettings>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!settings) {
      getSettings().then(s => { setSettings(s); setLocal(s) })
    } else {
      setLocal(settings)
    }
  }, [settings, setSettings])

  const save = async () => {
    setSaving(true)
    try { const s = await updateSettings(local); setSettings(s) } finally { setSaving(false) }
  }

  return (
    <div>
      <Header title="Settings" />
      <Card className="space-y-4">
        <div>
          <label className="block text-sm mb-1">STT Device</label>
          <input className="w-full bg-zinc-800 rounded px-3 py-2" value={local.stt_device || ''} onChange={e=>setLocal(v=>({...v, stt_device: e.target.value}))} />
        </div>
        <div>
          <label className="block text-sm mb-1">TTS Voice</label>
          <input className="w-full bg-zinc-800 rounded px-3 py-2" value={local.tts_voice || ''} onChange={e=>setLocal(v=>({...v, tts_voice: e.target.value}))} />
        </div>
        <div>
          <label className="block text-sm mb-1">Locale</label>
          <input className="w-full bg-zinc-800 rounded px-3 py-2" value={local.locale || ''} onChange={e=>setLocal(v=>({...v, locale: e.target.value}))} />
        </div>
        <div>
          <label className="block text-sm mb-1">OpenAI API Key</label>
          <input className="w-full bg-zinc-800 rounded px-3 py-2" value={local.openai_key || ''} onChange={e=>setLocal(v=>({...v, openai_key: e.target.value}))} />
        </div>
        <button onClick={save} disabled={saving} className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50">
          {saving ? 'Saving…' : 'Save'}
        </button>
      </Card>
    </div>
  )
}