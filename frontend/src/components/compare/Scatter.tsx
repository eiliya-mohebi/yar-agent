import { useCallback, useState, type MouseEvent } from 'react'
import { money } from '@/lib/format'
import type { CompareAggregate } from '@/lib/types'

type Point = { a: CompareAggregate; x: number; y: number }

function buildPoints(agg: CompareAggregate[]): {
  points: Point[]
  useQuality: boolean
} {
  const useQuality = agg.some((a) => a.quality_avg != null)
  const points = agg
    .map((a) => {
      let y: number | null = null
      if (useQuality && a.quality_avg != null) y = a.quality_avg
      else if (!useQuality && a.cases_scored) {
        y = ((a.cases_passed ?? 0) / (a.cases_scored ?? 1)) * 10
      }
      return { a, x: a.total_cost_usd ?? 0, y }
    })
    .filter((p): p is Point => p.y != null && p.x > 0)
  return { points, useQuality }
}

export function Scatter({ aggregate }: { aggregate: CompareAggregate[] }) {
  const { points, useQuality } = buildPoints(aggregate)
  const [tip, setTip] = useState<{ text: string; x: number; y: number } | null>(
    null,
  )

  const onMove = useCallback((e: MouseEvent, text: string) => {
    setTip({ text, x: e.clientX + 14, y: e.clientY + 12 })
  }, [])

  if (points.length < 2) return null

  const W = 640
  const H = 300
  const L = 46
  const R = 150
  const T = 16
  const B = 36
  const xmax = Math.max(...points.map((p) => p.x)) * 1.08 || 1
  const px = (x: number) => L + (x / xmax) * (W - L - R)
  const py = (y: number) => H - B - (y / 10) * (H - T - B)

  const yCriteria = useQuality
    ? 'Referee grade — 0-10, scored by a model that is not racing.'
    : 'Completion — fraction of the task checklist met. Deterministic, no judge.'
  const yLabel = useQuality ? 'referee grade' : 'completion'

  const sorted = [...points].sort((a, b) => a.x - b.x)

  return (
    <div className="card mt-3.5 px-3.5 py-3">
      <div className="meta mb-1">
        Cost vs {useQuality ? 'quality (referee grade)' : 'completion'} — cheap and
        good is top-left
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="scatter"
        preserveAspectRatio="xMidYMid meet"
        dir="ltr"
      >
        <line x1={L} y1={T} x2={L} y2={H - B} className="sc-axis" />
        <line x1={L} y1={H - B} x2={W - R} y2={H - B} className="sc-axis" />
        {[0, 2, 4, 6, 8, 10].map((v) => (
          <g key={v}>
            <line
              x1={L}
              y1={py(v)}
              x2={W - R}
              y2={py(v)}
              className="sc-grid"
            />
            <text x={L - 6} y={py(v) + 3} className="sc-tick" textAnchor="end">
              {v}
            </text>
          </g>
        ))}
        {sorted.map((p) => {
          const score = p.y
          const cls = score >= 7 ? 'hi' : score >= 4 ? 'mid' : 'lo'
          const cx = px(p.x)
          const cy = py(p.y)
          return (
            <g key={p.a.spec ?? p.a.model}>
              <circle cx={cx} cy={cy} r={5} className={`sc-dot ${cls}`} />
              <text x={cx + 9} y={cy + 3} className="sc-lbl">
                {p.a.model} · {money(p.x)}
              </text>
            </g>
          )
        })}
        <text
          x={L + (W - R - L) / 2}
          y={H - 6}
          className="sc-tick"
          textAnchor="middle"
        >
          total cost →
        </text>
        <text
          x={14}
          y={T + (H - B - T) / 2}
          className="sc-tick sc-ylabel"
          textAnchor="middle"
          transform={`rotate(-90 14 ${T + (H - B - T) / 2})`}
        >
          {yLabel} →
        </text>
        <rect
          className="sc-yhit"
          x={0}
          y={T}
          width={26}
          height={H - B - T}
          onMouseEnter={(e) => onMove(e, yCriteria)}
          onMouseMove={(e) => onMove(e, yCriteria)}
          onMouseLeave={() => setTip(null)}
        />
      </svg>
      {tip ? (
        <div
          className="sc-tip"
          style={{
            insetInlineStart: tip.x,
            top: tip.y,
            display: 'block',
          }}
          dir="ltr"
          dir="ltr"
        >
          {tip.text}
        </div>
      ) : null}
    </div>
  )
}
