import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  cssVar: '--nav-w' | '--dock-w'
  fromEnd: boolean
  min: number
  max: number
  onResize: (width: number) => void
  className?: string
}

/** Drag handle between columns. `fromEnd` measures from the inline-end edge (dock). */
export function Resizer({
  cssVar,
  fromEnd,
  min,
  max,
  onResize,
  className,
}: Props) {
  const dragging = useRef(false)

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return
      const rtl = document.documentElement.dir === 'rtl'
      let width: number
      if (fromEnd) {
        // Dock sits at inline-end: LTR → right edge, RTL → left edge.
        width = rtl ? e.clientX : window.innerWidth - e.clientX
      } else {
        // Nav sits at inline-start.
        width = rtl ? window.innerWidth - e.clientX : e.clientX
      }
      const clamped = Math.min(max, Math.max(min, width))
      document.documentElement.style.setProperty(cssVar, `${clamped}px`)
      onResize(clamped)
    }
    const onUp = () => {
      if (!dragging.current) return
      dragging.current = false
      document.body.classList.remove('resizing')
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [cssVar, fromEnd, max, min, onResize])

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      className={cn(
        'h-screen w-[5px] shrink-0 cursor-col-resize bg-transparent hover:bg-[var(--accent-soft)]',
        className,
      )}
      onMouseDown={(e) => {
        e.preventDefault()
        dragging.current = true
        document.body.classList.add('resizing')
      }}
    />
  )
}
