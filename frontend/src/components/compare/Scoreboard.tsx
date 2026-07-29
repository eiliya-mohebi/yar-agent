import { Scatter } from '@/components/compare/Scatter'
import { foldLiveAggregate, type BoardSort, type BoardSortKey } from '@/lib/compare'
import { money, secs } from '@/lib/format'
import type {
  CompareAggregate,
  CompareResult,
  CompareRun,
} from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  aggregate: CompareAggregate[]
  history: CompareRun[]
  order: string[]
  results: Record<string, CompareResult>
  running: boolean
  boardSort: BoardSort
  onBoardSort: (key: BoardSortKey) => void
  onClearAll: () => void
  onDeleteRun: (ts: string) => void
  onOpenRun: (idx: number) => void
}

function sortArrow(active: boolean, dir: 'asc' | 'desc'): string {
  if (!active) return ''
  return dir === 'asc' ? ' ▲' : ' ▼'
}

export function Scoreboard({
  aggregate,
  history,
  order,
  results,
  running,
  boardSort,
  onBoardSort,
  onClearAll,
  onDeleteRun,
  onOpenRun,
}: Props) {
  const agg = foldLiveAggregate(aggregate, order, results, running)
  const raceCount = history.length + (running ? 1 : 0)

  if (!agg.length && !history.length) return null

  const th = (key: BoardSortKey, label: string, title?: string) => (
    <th
      className={cn('cmp-th', boardSort.key === key && 'on')}
      onClick={() => onBoardSort(key)}
      title={title}
      dir="ltr"
    >
      {label}
      {sortArrow(boardSort.key === key, boardSort.dir)}
    </th>
  )

  const rows = [...agg].sort((x, y) => {
    const xv = (x[boardSort.key] as number | null | undefined) ?? 0
    const yv = (y[boardSort.key] as number | null | undefined) ?? 0
    return (Number(xv) - Number(yv)) * (boardSort.dir === 'asc' ? 1 : -1)
  })

  return (
    <>
      {agg.length ? (
        <>
          <h2 className="mt-[22px] flex items-center gap-2.5 text-base font-semibold">
            Scoreboard
            <span className="meta font-normal">
              — totals across {raceCount} race{raceCount === 1 ? '' : 's'}
            </span>
            <button
              type="button"
              className="reveal ms-auto text-xs"
              onClick={onClearAll}
            >
              clear all
            </button>
          </h2>
          <Scatter aggregate={agg} />
          <div className="card overflow-x-auto px-2 py-1">
            <table>
              <thead>
                <tr>
                  <th>model</th>
                  {th('cases_passed', 'solved')}
                  <th
                    className={cn(
                      'cmp-th',
                      boardSort.key === 'quality_avg' && 'on',
                    )}
                    onClick={() => onBoardSort('quality_avg')}
                    title="Referee mean 0-10 grade on replies"
                    dir="ltr"
                  >
                    grade
                    {sortArrow(boardSort.key === 'quality_avg', boardSort.dir)}
                  </th>
                  {th('runs', 'races')}
                  <th dir="ltr">ok</th>
                  {th('total_latency_ms', 'total time')}
                  {th('total_tokens_in', 'in tok')}
                  {th('total_tokens_out', 'out tok')}
                  {th('total_tokens', 'total tok')}
                  <th title="List price per million tokens, input / output" dir="ltr">
                    rate $/M
                  </th>
                  {th('total_cost_usd', 'total cost')}
                </tr>
              </thead>
              <tbody>
                {rows.map((a) => (
                  <tr key={a.spec ?? a.model}>
                    <td>
                      <code dir="ltr">{a.model}</code>
                    </td>
                    <td dir="ltr">
                      {a.cases_scored ? (
                        <span
                          className={cn(
                            'cmp-score',
                            a.cases_passed === a.cases_scored
                              ? 'pass'
                              : a.cases_passed
                                ? 'part'
                                : 'fail',
                          )}
                        >
                          {a.cases_passed}/{a.cases_scored}
                        </span>
                      ) : (
                        <span className="meta">—</span>
                      )}
                    </td>
                    <td dir="ltr">
                      {a.quality_avg != null ? (
                        <span
                          className={cn(
                            'cmp-q',
                            a.quality_avg >= 7
                              ? 'hi'
                              : a.quality_avg >= 4
                                ? 'mid'
                                : 'lo',
                          )}
                        >
                          {a.quality_avg}
                        </span>
                      ) : (
                        <span className="meta">—</span>
                      )}
                    </td>
                    <td className="meta" dir="ltr">
                      {a.runs}
                    </td>
                    <td className="meta" dir="ltr">
                      {a.ok}/{a.runs}
                    </td>
                    <td className="meta" dir="ltr">
                      {secs(a.total_latency_ms)}
                    </td>
                    <td className="meta" dir="ltr">
                      {a.total_tokens_in}
                    </td>
                    <td className="meta" dir="ltr">
                      {a.total_tokens_out}
                    </td>
                    <td className="meta" dir="ltr">
                      {a.total_tokens}
                    </td>
                    <td className="meta" dir="ltr">
                      {a.rate_in != null
                        ? `$${a.rate_in}/$${a.rate_out}`
                        : '—'}
                    </td>
                    <td className="meta text-[var(--good)]" dir="ltr">
                      {money(a.total_cost_usd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {history.length ? (
        <>
          <h2 className="mt-[18px] text-base font-semibold">
            Recent races{' '}
            <span className="meta font-normal">— click to reopen</span>
          </h2>
          <div className="card">
            {history.map((run, i) => (
              <div
                key={run.ts ?? i}
                className="pinrow cursor-pointer"
                role="button"
                tabIndex={0}
                onClick={() => onOpenRun(i)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') onOpenRun(i)
                }}
              >
                <code className="min-w-0 flex-1 break-all" dir="auto">
                  {(run.message || '').slice(0, 90)}
                </code>
                <span className="meta whitespace-nowrap" dir="ltr">
                  {(run.results || []).length} models ·{' '}
                  {(run.ts || '').slice(0, 16).replace('T', ' ')}
                </span>
                <button
                  type="button"
                  className="reveal del ms-2 text-sm"
                  title="Delete just this run"
                  onClick={(e) => {
                    e.stopPropagation()
                    if (run.ts) onDeleteRun(run.ts)
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </>
  )
}
