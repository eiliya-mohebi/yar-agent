import { Link } from 'react-router-dom'
import { RevealLink } from '@/components/layout/RevealLink'
import { PageHead } from '@/components/layout/PageHead'
import { useLang } from '@/hooks/useLang'
import { money, secs } from '@/lib/format'
import type { DashboardData, EvalReport, Stats, Turn } from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  data: DashboardData | null
  agoSec: number | null
  error?: string | null
}

type UsageBucket = {
  provider?: string
  date?: string
  calls: number
  in: number
  out: number
  cost: number
}

type EvalHistoryRow = {
  ran_at?: string
  deterministic?: string
  judge?: string
  suites?: {
    deterministic?: { passed?: number; failed?: number }
    judge?: { passed?: number; failed?: number }
  }
}

function Tile({
  value,
  label,
  moneyTone,
}: {
  value: string | number
  label: string
  moneyTone?: boolean
}) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3.5 py-3">
      <b
        className={cn(
          'block text-[19px] font-semibold tabular-nums',
          moneyTone && 'text-[var(--good)]',
        )}
        dir="ltr"
      >
        {value}
      </b>
      <span className="text-[11.5px] text-[var(--ink2)]">{label}</span>
    </div>
  )
}

function GateSplit({ s, t }: { s: Stats; t: ReturnType<typeof useLang>['t'] }) {
  const tot = s.gate_skips + s.gate_retrieves
  if (!tot) {
    return (
      <>
        <div className="mt-0.5 flex h-[26px] overflow-hidden rounded-md border border-[var(--line)]">
          <div className="flex w-full items-center justify-center bg-[var(--accent)] text-[11px] font-semibold text-white opacity-35" />
        </div>
        <div className="mt-1.5 text-[11.5px] text-[var(--ink3)]">{t.gateEmpty}</div>
      </>
    )
  }
  const skipPct = Math.round((s.gate_skips / tot) * 100)
  const retPct = 100 - skipPct
  return (
    <>
      <div className="mt-0.5 flex h-[26px] overflow-hidden rounded-md border border-[var(--line)]">
        <div
          className="flex min-w-0 items-center justify-center overflow-hidden bg-[var(--accent)] text-[11px] font-semibold whitespace-nowrap text-white"
          style={{ width: `${skipPct}%` }}
          dir="ltr"
        >
          {skipPct >= 14 ? `${s.gate_skips} ${t.gateSkipped}` : ''}
        </div>
        <div
          className="flex min-w-0 items-center justify-center overflow-hidden bg-[var(--warn)] text-[11px] font-semibold whitespace-nowrap text-white"
          style={{ width: `${retPct}%` }}
          dir="ltr"
        >
          {retPct >= 14 ? `${s.gate_retrieves} ${t.gateRetrieved}` : ''}
        </div>
      </div>
    </>
  )
}

function StatusPill({ status, label }: { status: string; label: string }) {
  return (
    <span
      className={cn(
        'inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold',
        status === 'pass' && 'border-[var(--good)] text-[var(--good)]',
        status === 'fail' && 'border-[var(--bad)] text-[var(--bad)]',
        status !== 'pass' && status !== 'fail' && 'border-[var(--line2)] text-[var(--ink2)]',
      )}
      dir="ltr"
    >
      {label}
    </span>
  )
}

function evalReportFields(report: EvalReport | null): {
  deterministic?: string
  judge?: string
  ran_at?: string
} {
  if (!report) return {}
  return {
    deterministic: typeof report.deterministic === 'string' ? report.deterministic : undefined,
    judge: typeof report.judge === 'string' ? report.judge : undefined,
    ran_at: typeof report.ran_at === 'string' ? report.ran_at : undefined,
  }
}

export function OpsPage({ data, agoSec, error }: Props) {
  const { t } = useLang()

  if (error && !data) {
    return (
      <>
        <PageHead title={t.ops} agoSec={agoSec} />
        <p className="text-[var(--bad)]">{error}</p>
      </>
    )
  }
  if (!data) {
    return (
      <>
        <PageHead title={t.ops} agoSec={agoSec} />
        <p className="text-[var(--ink3)]">…</p>
      </>
    )
  }

  const s = data.stats
  const u = data.usage || { calls: 0, total_in: 0, total_out: 0, total_cost: 0 }
  const byProvider = (u.by_provider || []) as UsageBucket[]
  const byDay = (u.by_day || []) as UsageBucket[]
  const evalHistory = (data.eval_history || []) as EvalHistoryRow[]
  const report = evalReportFields(data.eval_report)

  const decided = data.turns.filter((t): t is Turn & { gate: NonNullable<Turn['gate']> } =>
    Boolean(t.gate),
  )
  const slow = [...data.turns]
    .filter((t) => t.latency_ms != null)
    .sort((a, b) => (b.latency_ms ?? 0) - (a.latency_ms ?? 0))
    .slice(0, 6)

  const suiteCounts = (row: EvalHistoryRow) => {
    const fmt = (x?: { passed?: number; failed?: number }) =>
      x ? `${x.passed ?? 0} pass · ${x.failed ?? 0} fail` : '—'
    return `det ${fmt(row.suites?.deterministic)} · judge ${fmt(row.suites?.judge)}`
  }

  return (
    <>
      <PageHead title={t.ops} home={data.home} agoSec={agoSec} />
      <div className="grid grid-cols-[repeat(auto-fill,minmax(128px,1fr))] gap-2.5">
        <Tile value={money(u.total_cost)} label={t.spent} moneyTone />
        <Tile value={u.total_in.toLocaleString()} label={t.tokensInAll} />
        <Tile value={u.total_out.toLocaleString()} label={t.tokensOutAll} />
        <Tile value={u.calls.toLocaleString()} label={t.llmCalls} />
        <Tile value={secs(s.latency_avg)} label={t.avgTurn} />
        <Tile value={s.tool_errors} label={t.toolErrors} />
      </div>

      <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.spendTitle}
      </h2>
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-[12.5px] text-[var(--ink2)]">
        {t.spendBody}{' '}
        <RevealLink path="usage.jsonl">usage.jsonl</RevealLink>
      </div>

      {byProvider.length ? (
        <>
          <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
            {t.spendByProvider}
          </h2>
          <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)]">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                  <th className="px-3 py-2">provider</th>
                  <th className="px-3 py-2">calls</th>
                  <th className="px-3 py-2">tokens in</th>
                  <th className="px-3 py-2">tokens out</th>
                  <th className="px-3 py-2">cost</th>
                </tr>
              </thead>
              <tbody>
                {byProvider.map((p) => (
                  <tr key={p.provider}>
                    <td className="border-t border-[var(--line)] px-3 py-2">
                      <code dir="ltr">{p.provider}</code>
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2 tabular-nums" dir="ltr">
                      {p.calls}
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2 tabular-nums" dir="ltr">
                      {p.in.toLocaleString()}
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2 tabular-nums" dir="ltr">
                      {p.out.toLocaleString()}
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2 tabular-nums" dir="ltr">
                      {money(p.cost)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {byDay.length ? (
        <>
          <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
            {t.spendPerDay}
          </h2>
          <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)]">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                  <th className="px-3 py-2">day</th>
                  <th className="px-3 py-2">calls</th>
                  <th className="px-3 py-2">tokens in</th>
                  <th className="px-3 py-2">tokens out</th>
                  <th className="px-3 py-2">cost</th>
                </tr>
              </thead>
              <tbody>
                {byDay.map((r) => (
                  <tr key={r.date}>
                    <td className="border-t border-[var(--line)] px-3 py-2 text-[11.5px] text-[var(--ink3)]" dir="ltr">
                      {r.date}
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2 tabular-nums" dir="ltr">
                      {r.calls}
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2 tabular-nums" dir="ltr">
                      {r.in.toLocaleString()}
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2 tabular-nums" dir="ltr">
                      {r.out.toLocaleString()}
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2 tabular-nums" dir="ltr">
                      {money(r.cost)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.gateOpsTitle}
      </h2>
      <GateSplit s={s} t={t} />
      {decided.length ? (
        <>
          <p className="mt-2 mb-2 text-[11.5px] text-[var(--ink3)]">{t.gateDecisionsNote}</p>
          <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)]">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                  <th className="px-3 py-2">turn</th>
                  <th className="px-3 py-2">decision</th>
                  <th className="px-3 py-2">why</th>
                </tr>
              </thead>
              <tbody>
                {decided.slice(0, 10).map((turn, i) => (
                  <tr key={`${turn.ts}-${i}`}>
                    <td className="border-t border-[var(--line)] px-3 py-2" dir="auto">
                      {(turn.user_message || '').slice(0, 44)}
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2">
                      <StatusPill
                        status={turn.gate.decision === 'skip' ? 'skip' : 'pass'}
                        label={String(turn.gate.decision)}
                      />
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2 text-[11.5px] text-[var(--ink3)]" dir="auto">
                      {String(turn.gate.reason || '')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.releaseGateTitle}
      </h2>
      <div className="mb-3 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-[12.5px] text-[var(--ink2)]">
        {t.releaseGateBody}
      </div>
      {report.deterministic ? (
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3">
          <StatusPill status={report.deterministic} label={`deterministic · ${report.deterministic}`} />
          <span className="ms-2">
            <StatusPill
              status={report.judge === 'pass' ? 'pass' : report.judge === 'fail' ? 'fail' : 'skip'}
              label={`llm-judge · ${report.judge ?? '—'}`}
            />
          </span>
          <p className="mt-2 text-[11.5px] text-[var(--ink3)]" dir="ltr">
            last run {report.ran_at} — re-run with <code>make gate</code>
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]" dir="ltr">
          never run yet — run <code>make gate</code> to populate this
        </div>
      )}

      {evalHistory.length ? (
        <>
          <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
            {t.evalHistory}
          </h2>
          <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)]">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                  <th className="px-3 py-2">when</th>
                  <th className="px-3 py-2">deterministic</th>
                  <th className="px-3 py-2">llm-judge</th>
                  <th className="px-3 py-2">counts</th>
                </tr>
              </thead>
              <tbody>
                {evalHistory.map((row, i) => (
                  <tr key={`${row.ran_at}-${i}`}>
                    <td className="border-t border-[var(--line)] px-3 py-2 text-[11.5px] text-[var(--ink3)]" dir="ltr">
                      {(row.ran_at || '').replace('T', ' ').slice(0, 19)}
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2">
                      <StatusPill status={row.deterministic || ''} label={row.deterministic || '—'} />
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2">
                      <StatusPill
                        status={row.judge === 'pass' ? 'pass' : row.judge === 'fail' ? 'fail' : 'skip'}
                        label={row.judge || '—'}
                      />
                    </td>
                    <td className="border-t border-[var(--line)] px-3 py-2 text-[11.5px] text-[var(--ink3)]" dir="ltr">
                      {suiteCounts(row)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.slowestTurns}
      </h2>
      {slow.length ? (
        <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)]">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                <th className="px-3 py-2">turn</th>
                <th className="px-3 py-2">latency</th>
                <th className="px-3 py-2">cost</th>
                <th className="px-3 py-2">tools</th>
              </tr>
            </thead>
            <tbody>
              {slow.map((turn, i) => (
                <tr key={`${turn.ts}-${i}`}>
                  <td className="border-t border-[var(--line)] px-3 py-2" dir="auto">
                    {(turn.user_message || '').slice(0, 48)}
                  </td>
                  <td className="border-t border-[var(--line)] px-3 py-2 tabular-nums" dir="ltr">
                    {secs(turn.latency_ms)}
                  </td>
                  <td className="border-t border-[var(--line)] px-3 py-2 tabular-nums" dir="ltr">
                    {money(turn.cost || 0)}
                  </td>
                  <td className="border-t border-[var(--line)] px-3 py-2 font-mono text-[11.5px]" dir="ltr">
                    {(turn.tools || []).map((x) => x.tool).join(', ') || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
          {t.noTurns}
        </div>
      )}

      <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.tracingTitle}
      </h2>
      {(data.trace_errors || []).map((e) => (
        <div key={e.file} className="mb-2 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3">
          <StatusPill status="fail" label="trace encoding error" />
          <p className="mt-2 text-[11.5px] text-[var(--ink3)]" dir="ltr">
            <code>{e.file}</code> — {e.error}
          </p>
        </div>
      ))}
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-[12.5px] text-[var(--ink2)]">
        {s.trace_files} trace file(s) in <code>traces/</code>
        {data.trace_file ? (
          <>
            {' '}
            (newest: <code>{data.trace_file}</code>)
          </>
        ) : null}
        . <RevealLink path="traces">{t.openTraces}</RevealLink>. {t.traceTailNote}
      </div>
      {(data.trace_tail || []).length ? (
        <div className="mt-3 overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)]">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                <th className="px-3 py-2">event</th>
                <th className="px-3 py-2">detail</th>
                <th className="px-3 py-2">when</th>
              </tr>
            </thead>
            <tbody>
              {data.trace_tail.map((e, i) => (
                <tr key={`${e.ts}-${i}`}>
                  <td className="border-t border-[var(--line)] px-3 py-2">
                    <code dir="ltr">{e.type}</code>
                  </td>
                  <td className="border-t border-[var(--line)] px-3 py-2 text-[11.5px] text-[var(--ink3)]" dir="auto">
                    {String(e.detail || '').slice(0, 60)}
                  </td>
                  <td className="border-t border-[var(--line)] px-3 py-2 text-[11.5px] text-[var(--ink3)]" dir="ltr">
                    {(e.ts || '').replace('T', ' ').slice(0, 19)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="mt-3 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
          {t.noTraceLines}
        </div>
      )}
      <p className="mt-2 text-[11.5px] text-[var(--ink3)]" dir="ltr">
        {t.traceOtelHint}
      </p>
      <p className="mt-2 text-[11.5px]">
        <Link to="/memory/consolidation" className="text-[var(--accent)] underline">
          {t.memory}
        </Link>{' '}
        · consolidation runs are traced here too.
      </p>
    </>
  )
}
