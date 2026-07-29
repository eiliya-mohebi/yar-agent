import { MarkdownText } from '@/components/chat/Markdown'
import {
  compareErrorReason,
  metricValue,
  modelFromSpec,
  qualityScore,
  toSpec,
  type SortMetric,
} from '@/lib/compare'
import { money, secs } from '@/lib/format'
import type { CompareResult } from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  order: string[]
  results: Record<string, CompareResult>
  sortBy: SortMetric
  running: boolean
  grading: { n?: number; judge?: string; done?: number } | null
  raceError: string | null
  regrading: boolean
  onSort: (key: SortMetric) => void
  onRegradeRun: () => void
  onClearCards: () => void
  onGradeCard: (spec: string) => void
}

function GateBadge({ gate }: { gate: CompareResult['gate'] }) {
  const decision =
    gate == null
      ? '…'
      : typeof gate === 'object'
        ? (gate.decision ?? '…')
        : String(gate)
  const retrieve = decision === 'retrieve'
  return (
    <span className={cn('badge', retrieve && 'retrieve')}>
      gate · {decision}
    </span>
  )
}

function CompareCol({
  res,
  sortBy,
  onGrade,
}: {
  res: CompareResult
  sortBy: SortMetric
  onGrade: () => void
}) {
  const spec = res.spec || toSpec(res.model || '')
  const modelId = res.model || modelFromSpec(spec)

  if (res.error) {
    const why = compareErrorReason(res.error)
    return (
      <div className="cmp-col err">
        <div className="cmp-h">
          <code dir="ltr">{modelId}</code>
          <span className="badge">error</span>
        </div>
        {why ? (
          <div className="meta text-[var(--bad)]">
            <b>{why}</b>
          </div>
        ) : null}
        <div className="meta opacity-70" dir="ltr">
          {res.error}
        </div>
      </div>
    )
  }

  const tools = (res.tools || []).map((t, i) => {
    const name = typeof t === 'string' ? t : t.tool
    return (
      <span key={`${name}-${i}`} className="stage done">
        tool · {name}
      </span>
    )
  })

  const gateBadge = <GateBadge gate={res.gate} />

  if (res.streaming) {
    return (
      <div className="cmp-col">
        <div className="cmp-h">
          <code dir="ltr">{modelId}</code>
          <span className="live-dot" />
        </div>
        <div className="cmp-stats">{gateBadge}</div>
        {tools.length ? (
          <div className="stages flex flex-wrap">{tools}</div>
        ) : null}
        <div className="meta">
          {(res.tools || []).length ? 'running tools…' : 'thinking…'}{' '}
          <span className="caret" />
        </div>
      </div>
    )
  }

  const c = res.completion
  const qs = qualityScore(res.quality)
  const completionBadge = c ? (
    <span
      className={cn('cmp-score', c.passed ? 'pass' : 'fail')}
      title={c.why || ''}
    >
      {c.passed ? 'solved' : `failed · ${c.why || ''}`}
    </span>
  ) : null
  const qualityBadge =
    qs != null ? (
      <span
        className={cn('cmp-q', qs >= 7 ? 'hi' : qs >= 4 ? 'mid' : 'lo')}
        title={
          typeof res.quality === 'object' && res.quality
            ? `${qs}/10 — ${res.quality.reason || ''}`
            : `${qs}/10`
        }
        dir="ltr"
      >
        {qs}/10
      </span>
    ) : null

  return (
    <div
      className={cn(
        'cmp-col',
        c && (c.passed ? 'solved' : 'failed'),
      )}
    >
      <div className="cmp-h">
        <code dir="ltr">{modelId}</code>
        {completionBadge}
        {qualityBadge}
        <button
          type="button"
          className="reveal cmp-grade1"
          title="Grade this card with the referee"
          onClick={onGrade}
          dir="ltr"
        >
          {res._grading ? 'grading…' : qs != null ? 're-grade' : 'grade'}
        </button>
      </div>
      <div className="cmp-stats">
        {gateBadge}
        <span
          className={cn('chip', sortBy === 'latency' && 'sorted')}
          dir="ltr"
        >
          {secs(res.latency_ms)}
        </span>
        <span className="chip" dir="ltr">
          {res.iterations ?? '?'} iter
        </span>
        <span
          className={cn('chip', sortBy === 'cost' && 'money')}
          dir="ltr"
        >
          {money(res.cost_usd ?? 0)}
        </span>
        <span
          className={cn('chip', sortBy === 'tokens' && 'sorted')}
          dir="ltr"
        >
          {(res.tokens_in ?? 0) + (res.tokens_out ?? 0)} tok
        </span>
      </div>
      {tools.length ? (
        <div className="stages flex flex-wrap">{tools}</div>
      ) : null}
      <MarkdownText text={res.reply || ''} className="cmp-reply" dir="auto" />
    </div>
  )
}

export function ResultCols({
  order,
  results,
  sortBy,
  running,
  grading,
  raceError,
  regrading,
  onSort,
  onRegradeRun,
  onClearCards,
  onGradeCard,
}: Props) {
  if (!order.length) return null

  const done = order
    .map((id) => results[toSpec(id)])
    .filter((r): r is CompareResult => Boolean(r))
    .filter((r) => !r.error && !r.streaming)

  const keyFn = (id: string) => metricValue(results[toSpec(id)] ?? {}, sortBy)

  const rank = (id: string): [number, number] => {
    const r = results[toSpec(id)]
    if (!r) return [2, 0]
    if (r.error) return [3, 0]
    if (r.streaming) return [1, 0]
    return [0, keyFn(id)]
  }

  const shown = [...order].sort((a, b) => {
    const ra = rank(a)
    const rb = rank(b)
    return ra[0] - rb[0] || ra[1] - rb[1]
  })

  const sorters: [SortMetric, string][] = [
    ['latency', 'seconds'],
    ['tokens', 'tokens'],
    ['cost', 'money'],
  ]

  const summary =
    done.length < order.length
      ? `Racing ${order.length} models — ${done.length}/${order.length} done`
      : grading
        ? `Referee ${grading.judge || ''} grading — ${grading.done ?? 0}/${grading.n ?? 0} scored`
        : ''

  return (
    <div className="mt-3">
      {summary ? <div className="meta mb-1.5">{summary}</div> : null}
      {(done.length || order.length) && !running ? (
        <div className="cmp-sortbar">
          {done.length
            ? sorters.map(([k, label]) => (
                <button
                  key={k}
                  type="button"
                  className={cn('cmp-sortbtn', sortBy === k && 'on')}
                  onClick={() => onSort(k)}
                  dir="ltr"
                >
                  {label}
                </button>
              ))
            : null}
          {done.length ? (
            <button
              type="button"
              className="reveal ms-auto text-xs"
              title="Re-run the referee on every model in this run"
              onClick={onRegradeRun}
              disabled={regrading}
              dir="ltr"
            >
              {regrading ? 're-grading…' : 're-grade run'}
            </button>
          ) : null}
          {order.length ? (
            <button
              type="button"
              className={cn('reveal text-xs', !done.length && 'ms-auto')}
              onClick={onClearCards}
              dir="ltr"
            >
              clear cards
            </button>
          ) : null}
        </div>
      ) : null}
      <div className="cmp-grid">
        {shown.map((modelId) => {
          const spec = toSpec(modelId)
          const r = results[spec]
          if (r) {
            return (
              <CompareCol
                key={spec}
                res={r}
                sortBy={sortBy}
                onGrade={() => onGradeCard(spec)}
              />
            )
          }
          return (
            <div key={spec} className="cmp-col">
              <div className="cmp-h">
                <code dir="ltr">{modelId}</code>
              </div>
              <div className="meta">
                racing… <span className="caret" />
              </div>
            </div>
          )
        })}
      </div>
      {raceError ? (
        <div className="meta mt-2 text-[var(--bad)]" dir="ltr">
          {raceError}
        </div>
      ) : null}
    </div>
  )
}
