import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { STAGE, type TraceEvent } from '@/components/diagram/stage'
import { api } from '@/lib/api'

const POLL_MS = 450
const STAGGER_MS = 620
const FLASH_MS = 1000

const RETRIEVE_NODES = ['procedural', 'semantic', 'episodic'] as const
const RETRIEVE_EDGES = ['e-gate-proc', 'e-gate-sem', 'e-gate-epi'] as const

function flashAdd(
  ids: readonly string[],
  setter: Dispatch<SetStateAction<Set<string>>>,
) {
  setter((prev) => {
    const next = new Set(prev)
    ids.forEach((id) => next.add(id))
    return next
  })
  window.setTimeout(() => {
    setter((prev) => {
      const next = new Set(prev)
      ids.forEach((id) => next.delete(id))
      return next
    })
  }, FLASH_MS)
}

export function useTraceEvents() {
  const [statusLabel, setStatusLabel] = useState('')
  const [hotNodes, setHotNodes] = useState<Set<string>>(() => new Set())
  const [liveEdges, setLiveEdges] = useState<Set<string>>(() => new Set())
  const [animating, setAnimating] = useState(false)

  const cursorRef = useRef<number | null>(null)
  const queueRef = useRef<TraceEvent[]>([])
  const playingRef = useRef(false)

  useEffect(() => {
    const animateStage = (ev: TraceEvent) => {
      const type = ev.type ?? ''
      const spec = STAGE[type]
      if (!spec) return

      setStatusLabel(spec.label)
      flashAdd(spec.nodes, setHotNodes)
      flashAdd(spec.edges, setLiveEdges)

      if (type === 'gate' && ev.decision === 'retrieve') {
        flashAdd(RETRIEVE_NODES, setHotNodes)
        flashAdd(RETRIEVE_EDGES, setLiveEdges)
      }
    }

    const playNext = () => {
      if (!queueRef.current.length) {
        playingRef.current = false
        setAnimating(false)
        setStatusLabel('')
        return
      }

      playingRef.current = true
      setAnimating(true)
      animateStage(queueRef.current.shift()!)
      window.setTimeout(playNext, STAGGER_MS)
    }

    const poll = async () => {
      try {
        const r = await api.events(cursorRef.current)
        if (cursorRef.current != null && r.events.length) {
          queueRef.current.push(...r.events)
          if (!playingRef.current) playNext()
        }
        cursorRef.current = r.cursor
      } catch {
        // server busy
      }
    }

    const id = window.setInterval(() => {
      void poll()
    }, POLL_MS)
    void poll()

    return () => window.clearInterval(id)
  }, [])

  return { statusLabel, hotNodes, liveEdges, animating }
}
