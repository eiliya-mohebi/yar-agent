import { useCallback, useEffect, useState } from 'react'

const DEFAULT_NAV = 208
const DEFAULT_DOCK = 380
const NAV_MIN = 150
const NAV_MAX = 380
const DOCK_MIN = 260
const DOCK_MAX = 680

function readNumber(key: string, fallback: number): number {
  try {
    const raw = localStorage.getItem(key)
    if (raw == null) return fallback
    const n = Number(raw)
    return Number.isFinite(n) ? n : fallback
  } catch {
    return fallback
  }
}

function readFlag(key: string): boolean | null {
  try {
    const raw = localStorage.getItem(key)
    if (raw == null) return null
    return raw === '1'
  } catch {
    return null
  }
}

function writeFlag(key: string, value: boolean): void {
  try {
    localStorage.setItem(key, value ? '1' : '0')
  } catch {
    // ignore
  }
}

export type ChromeState = {
  navW: number
  dockW: number
  navHidden: boolean
  dockClosed: boolean
  showTele: boolean
  setNavW: (w: number) => void
  setDockW: (w: number) => void
  setNavHidden: (v: boolean) => void
  setDockClosed: (v: boolean) => void
  toggleTele: () => void
  clampNav: (w: number) => number
  clampDock: (w: number) => number
}

export function useLocalChrome(): ChromeState {
  const [navW, setNavWState] = useState(() => readNumber('navW', DEFAULT_NAV))
  const [dockW, setDockWState] = useState(() => readNumber('dockW', DEFAULT_DOCK))
  const [navHidden, setNavHiddenState] = useState(
    () => readFlag('navHidden') === true,
  )
  const [dockClosed, setDockClosedState] = useState(() => {
    const saved = readFlag('dockClosed')
    if (saved === null) return window.innerWidth < 1180
    return saved
  })
  const [showTele, setShowTele] = useState(() => {
    try {
      return localStorage.getItem('yar_tele') !== '0'
    } catch {
      return true
    }
  })

  useEffect(() => {
    document.documentElement.style.setProperty('--nav-w', `${navW}px`)
  }, [navW])

  useEffect(() => {
    document.documentElement.style.setProperty('--dock-w', `${dockW}px`)
  }, [dockW])

  useEffect(() => {
    document.body.classList.toggle('no-tele', !showTele)
  }, [showTele])

  const clampNav = useCallback(
    (w: number) => Math.min(NAV_MAX, Math.max(NAV_MIN, w)),
    [],
  )
  const clampDock = useCallback(
    (w: number) => Math.min(DOCK_MAX, Math.max(DOCK_MIN, w)),
    [],
  )

  const setNavW = useCallback(
    (w: number) => {
      const next = clampNav(w)
      setNavWState(next)
      try {
        localStorage.setItem('navW', String(next))
      } catch {
        // ignore
      }
    },
    [clampNav],
  )

  const setDockW = useCallback(
    (w: number) => {
      const next = clampDock(w)
      setDockWState(next)
      try {
        localStorage.setItem('dockW', String(next))
      } catch {
        // ignore
      }
    },
    [clampDock],
  )

  const setNavHidden = useCallback((v: boolean) => {
    setNavHiddenState(v)
    writeFlag('navHidden', v)
  }, [])

  const setDockClosed = useCallback((v: boolean) => {
    setDockClosedState(v)
    writeFlag('dockClosed', v)
  }, [])

  const toggleTele = useCallback(() => {
    setShowTele((prev) => {
      const next = !prev
      try {
        localStorage.setItem('yar_tele', next ? '1' : '0')
      } catch {
        // ignore
      }
      return next
    })
  }, [])

  return {
    navW,
    dockW,
    navHidden,
    dockClosed,
    showTele,
    setNavW,
    setDockW,
    setNavHidden,
    setDockClosed,
    toggleTele,
    clampNav,
    clampDock,
  }
}
