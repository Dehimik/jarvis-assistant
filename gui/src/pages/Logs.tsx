import Header from '@/components/Header'
import Card from '@/components/Card'
import { useEffect, useRef, useState } from 'react'
import {connectLogsWS, getLogFilePath} from '@/api/api'
import { open } from '@tauri-apps/plugin-shell'

export default function Logs() {
  const [lines, setLines] = useState<string[]>([])
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const ws = connectLogsWS()
    ws.onmessage = (e) => setLines(prev => [...prev, e.data as string].slice(-2000))
    ws.onerror = console.error
    return () => ws.close()
  }, [])

  useEffect(() => {
    if (boxRef.current) {
      boxRef.current.scrollTop = boxRef.current.scrollHeight
    }
  }, [lines])

  const handleOpenLogFile = async () => {
    try {
      const filePath = await getLogFilePath() // Отримуємо шлях з бекенду
      await open(filePath) // Відкриваємо його через Tauri
    } catch (error) {
      console.error('Failed to open log file:', error)
      // Тут можна показати сповіщення про помилку
    }
  }

  return (
    <div>
      <Header title="Logs" />
        <div className="mb-4">
          <button
            onClick={handleOpenLogFile}
            className="px-4 py-2 mt-4 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors">
            Open log file in redactor
          </button>
        </div>
      <Card>
        <div ref={boxRef} className="h-[70vh] overflow-auto font-mono text-sm whitespace-pre-wrap">
          {lines.join('\n')}
        </div>
      </Card>
    </div>
  )
}