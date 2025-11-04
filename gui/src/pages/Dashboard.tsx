import Header from '@/components/Header'
import Card from '@/components/Card'
import { useEffect } from 'react'
import { getStatus } from '@/api/api'
import { useJarvisStore } from '@/store/store'
import StatusControls from "@/components/StatusControls.tsx";

export default function Dashboard() {
  const { status, setStatus } = useJarvisStore()

  useEffect(() => {
    getStatus().then(setStatus).catch(console.error)
  }, [setStatus])

  return (
    <div>
      <Header title="Dashboard" />
      <div style={{marginBottom:24}}>
        <StatusControls />
      </div>
      <div className="grid md:grid-cols-3 gap-4">
        <Card>
          <div className="text-sm opacity-70 mb-1">Service</div>
          <div className="text-xl font-semibold">{status?.online ? 'Online' : 'Offline'}</div>
        </Card>
        <Card>
          <div className="text-sm opacity-70 mb-1">Listening</div>
          <div className="text-xl font-semibold">{status?.listening ? 'Yes' : 'No'}</div>
        </Card>
        <Card>
          <div className="text-sm opacity-70 mb-1">Speaking</div>
          <div className="text-xl font-semibold">{status?.speaking ? 'Yes' : 'No'}</div>
        </Card>
      </div>
    </div>
  )
}