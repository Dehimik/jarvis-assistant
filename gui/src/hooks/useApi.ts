import { useEffect, useState } from 'react'

export function useAsync<T>(fn: () => Promise<T>, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    fn().then(r => { if (alive) setData(r) }).catch(setError).finally(() => alive && setLoading(false))
    return () => { alive = false }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, loading, error }
}