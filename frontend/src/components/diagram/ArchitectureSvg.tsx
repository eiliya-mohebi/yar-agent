import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { archSvg } from '@/components/diagram/archSvg'
import type { DashboardData } from '@/lib/types'

const NODE_ROUTES: Record<string, string> = {
  gateway: '/gateway',
  wm: '/memory',
  llm: '/loop',
  tools: '/tools',
  reply: '/loop',
  gate: '/memory',
  procedural: '/memory/skills',
  semantic: '/memory/semantic',
  episodic: '/memory/episodic',
  consolidation: '/memory/consolidation',
  trace: '/ops',
}

type Props = {
  data: DashboardData
  animating?: boolean
  hotNodes?: Set<string>
  liveEdges?: Set<string>
}

export function ArchitectureSvg({ data, animating = false, hotNodes, liveEdges }: Props) {
  const navigate = useNavigate()
  const wrapRef = useRef<HTMLDivElement>(null)
  const frozenRef = useRef(data)

  if (!animating) {
    frozenRef.current = data
  }

  useEffect(() => {
    const el = wrapRef.current
    if (!el || animating) return
    el.innerHTML = archSvg(frozenRef.current)
  }, [data, animating])

  useEffect(() => {
    const root = wrapRef.current
    if (!root) return

    root.querySelectorAll('[data-node]').forEach((node) => node.classList.remove('hot'))
    root.querySelectorAll('[data-edge]').forEach((edge) => edge.classList.remove('live'))

    hotNodes?.forEach((id) => {
      root.querySelectorAll(`[data-node="${id}"]`).forEach((node) => node.classList.add('hot'))
    })
    liveEdges?.forEach((id) => {
      root.querySelectorAll(`[data-edge="${id}"]`).forEach((edge) => edge.classList.add('live'))
    })
  }, [hotNodes, liveEdges, data, animating])

  useEffect(() => {
    const root = wrapRef.current
    if (!root) return

    const onClick = (ev: MouseEvent) => {
      const target = (ev.target as Element | null)?.closest('[data-node]')
      if (!target || !root.contains(target)) return
      const id = target.getAttribute('data-node')
      if (!id) return
      const route = NODE_ROUTES[id]
      if (route) navigate(route)
    }

    root.addEventListener('click', onClick)
    return () => root.removeEventListener('click', onClick)
  }, [navigate, data, animating])

  return <div ref={wrapRef} dir="ltr" />
}
