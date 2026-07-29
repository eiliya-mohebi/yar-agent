import { MarkdownText } from '@/components/chat/Markdown'
import { money, secs } from '@/lib/format'
import type { Turn } from '@/lib/types'
import { cn } from '@/lib/utils'

export function TurnCard({ turn }: { turn: Turn }) {
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
