import { MarkdownText } from '@/components/chat/Markdown'
import { PageHead } from '@/components/layout/PageHead'
import { useLang } from '@/hooks/useLang'
import { money, secs } from '@/lib/format'
import type { DashboardData, Stats, Turn } from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  data: DashboardData | null
  agoSec: number | null
  error: string | null
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

function GateSplit({
  s,
  caption,
  empty,
  skippedLabel,
  retrievedLabel,
}: {
  s: Stats
  caption: string
  empty: string
  skippedLabel: string
  retrievedLabel: string
}) {
  const tot = s.gate_skips + s.gate_retrieves
  if (!tot) {
    return (
      <>
        <div className="mt-0.5 flex h-[26px] overflow-hidden rounded-md border border-[var(--line)]">
          <div className="flex w-full items-center justify-center bg-[var(--accent)] text-[11px] font-semibold text-white opacity-35" />
        </div>
        <div className="mt-1.5 text-[11.5px] text-[var(--ink3)]">{empty}</div>
      </>
    )
  }
  const skipPct = Math.round((s.gate_skips / tot) * 100)
  const retPct = 100 - skipPct
  const seg = (cls: string, n: number, label: string, pct: number) => (
    <div
      className={cn(
        'flex min-w-0 items-center justify-center overflow-hidden text-[11px] font-semibold whitespace-nowrap text-white',
        cls === 'skip' ? 'bg-[var(--accent)]' : 'bg-[var(--warn)]',
      )}
      style={{ width: `${pct}%` }}
      dir="ltr"
    >
      {pct >= 14 ? `${n} ${label}` : ''}
    </div>
  )
  return (
    <>
      <div className="mt-0.5 flex h-[26px] overflow-hidden rounded-md border border-[var(--line)]">
        {seg('skip', s.gate_skips, skippedLabel, skipPct)}
        {seg('ret', s.gate_retrieves, retrievedLabel, retPct)}
      </div>
      <div className="mt-1.5 text-[11.5px] text-[var(--ink3)]">{caption}</div>
    </>
  )
}

function TurnCard({ turn }: { turn: Turn }) {
  return (
    <div className="mb-2.5 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5">
      <div className="font-medium" dir="auto">
        {turn.user_message || ''}
      </div>
      {turn.gate ? (
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span
            className={cn(
              'inline-block rounded-full border border-[var(--line2)] px-2 py-0.5 text-[11px] text-[var(--ink2)]',
              turn.gate.decision === 'retrieve' &&
                'border-[var(--accent)] text-[var(--accent)]',
            )}
            dir="ltr"
          >
            gate · {turn.gate.decision}
          </span>
          <span className="text-[11.5px] text-[var(--ink3)]" dir="auto">
            {String(turn.gate.reason || '')}
          </span>
        </div>
      ) : null}
      {(turn.tools || []).map((x, i) => (
        <div
          key={`${x.tool}-${i}`}
          className={cn(
            'mt-2 rounded-[7px] border border-[var(--line)] bg-[var(--bg)] px-2.5 py-2 text-[12.5px]',
            x.status === 'error' && 'border-[var(--bad)] bg-[var(--bad-soft)]',
          )}
        >
          <code className="font-mono" dir="ltr">
            {x.tool}
          </code>
          {x.summary ? (
            <span className="ms-2 text-[var(--ink2)]" dir="auto">
              {x.summary}
            </span>
          ) : null}
        </div>
      ))}
      {turn.reply ? (
        <div className="mt-2">
          <MarkdownText text={turn.reply} />
        </div>
      ) : null}
      <div className="mt-2 font-mono text-[11.5px] text-[var(--ink3)] tabular-nums" dir="ltr">
        {(turn.ts || '').replace('T', ' ').slice(0, 19)} · {secs(turn.latency_ms)} ·{' '}
        {turn.iterations ?? '?'} iter · {money(turn.cost || 0)}
        {turn.consolidation
          ? ` · consolidated ${turn.consolidation.new_facts ?? 0} fact(s)`
          : ''}
      </div>
    </div>
  )
}

export function OverviewPage({ data, agoSec, error }: Props) {
  const { t } = useLang()
  if (error && !data) {
    return (
      <>
        <PageHead title={t.overview} agoSec={agoSec} />
        <p className="text-[var(--bad)]">{error}</p>
      </>
    )
  }
  if (!data) {
    return (
      <>
        <PageHead title={t.overview} agoSec={agoSec} />
        <p className="text-[var(--ink3)]">…</p>
      </>
    )
  }

  const s = data.stats
  const u = data.usage || { total_cost: 0 }
  const skipPct =
    s.gate_skips + s.gate_retrieves
      ? Math.round((s.gate_skips / (s.gate_skips + s.gate_retrieves)) * 100)
      : 0

  return (
    <>
      <PageHead title={t.overview} home={data.home} agoSec={agoSec} />
      <div className="grid grid-cols-[repeat(auto-fill,minmax(128px,1fr))] gap-2.5">
        <Tile value={money(u.total_cost)} label={t.spent} moneyTone />
        <Tile value={secs(s.latency_avg)} label={t.avgTurn} />
        <Tile value={s.turns} label={t.turns} />
        <Tile value={s.tool_calls} label={t.toolCalls} />
        <Tile value={data.facts.length} label={t.facts} />
        <Tile value={data.calendar.length} label={t.events} />
      </div>

      <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.gateHero}
      </h2>
      <GateSplit
        s={s}
        caption={t.gateCaption(skipPct)}
        empty={t.gateEmpty}
        skippedLabel={t.gateSkipped}
        retrievedLabel={t.gateRetrieved}
      />

      <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.architecture}
      </h2>
      <div className="rounded-lg border border-dashed border-[var(--line2)] bg-[var(--panel)] px-4 py-6 text-[var(--ink3)]">
        {t.architectureSoon}
      </div>

      <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.latestTurn}
      </h2>
      {data.turns.length ? (
        <TurnCard turn={data.turns[0]!} />
      ) : (
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
          {t.noTurns}
        </div>
      )}
    </>
  )
}
