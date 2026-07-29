import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'
import type { DashboardData } from '@/lib/types'

const POLL_MS = 5000

export function useDashboardData() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [updatedAt, setUpdatedAt] = useState<number | null>(null)
  const [tick, setTick] = useState(0)
  const mounted = useRef(true)

  const refresh = useCallback(async () => {
    try {
      const next = await api.data()
      if (!mounted.current) return
      setData(next)
      setError(null)
      setUpdatedAt(Date.now())
    } catch (err) {
      if (!mounted.current) return
      const message = err instanceof Error ? err.message : 'Failed to load /api/data'
      setError(message)
    }
  }, [])

  useEffect(() => {
    mounted.current = true
    void refresh()
    const poll = window.setInterval(() => void refresh(), POLL_MS)
    const clock = window.setInterval(() => setTick((t) => t + 1), 1000)
    return () => {
      mounted.current = false
      window.clearInterval(poll)
      window.clearInterval(clock)
    }
  }, [refresh])

  const agoSec =
    updatedAt == null ? null : Math.max(0, Math.round((Date.now() - updatedAt) / 1000))

  return { data, error, refresh, agoSec, tick }
}
