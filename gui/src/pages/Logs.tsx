import Header from '@/components/Header'
import Card from '@/components/Card'
import { useEffect, useRef, useState } from 'react'
import { connectLogsWS } from '@/api/api'

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

  return (
    <div>
      <Header title="Logs" />
      <Card>
        <div ref={boxRef} className="h-[70vh] overflow-auto font-mono text-sm whitespace-pre-wrap">
          {lines.join('\n')}
        </div>
      </Card>
    </div>
  )
}