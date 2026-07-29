import { PageHead } from '@/components/layout/PageHead'
import { useLang } from '@/hooks/useLang'
import type { DashboardData, SessionRow } from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  data: DashboardData | null
  agoSec: number | null
  error?: string | null
  onOpenSession?: (id: string) => void
}

function SourceTag({ src }: { src: string }) {
  return (
    <span
      className={cn(
        'ms-1.5 inline-block rounded px-1.5 py-px text-[10px] font-semibold uppercase',
        src === 'dashboard' && 'bg-[var(--accent-soft)] text-[var(--accent)]',
        src === 'cli' && 'bg-[var(--bg)] text-[var(--ink2)]',
      )}
      dir="ltr"
    >
      {src}
    </span>
  )
}

function SessionCard({
  session,
  active,
  onOpen,
}: {
  session: SessionRow
  active: boolean
  onOpen?: (id: string) => void
}) {
  const tags = (session.sources || []).map((src) => (
    <SourceTag key={src} src={src} />
  ))
  return (
    <button
      type="button"
      className={cn(
        'mb-2 w-full cursor-pointer rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-start transition-colors hover:border-[var(--line2)]',
        active && 'border-[var(--accent)]',
      )}
      onClick={() => onOpen?.(session.id)}
    >
      <div className="flex items-baseline justify-between gap-2.5">
        <span className="min-w-0 font-semibold" dir="auto">
          {session.title || session.id}
          {tags}
        </span>
        <span className="shrink-0 text-[11.5px] font-normal whitespace-nowrap text-[var(--ink3)] tabular-nums" dir="ltr">
          {session.messages ?? 0} msg ·{' '}
          {(session.last_at || '').slice(0, 16).replace('T', ' ')}
        </span>
      </div>
      <div className="mt-1 truncate text-[12.5px] text-[var(--ink2)]" dir="auto">
        {session.last || ''}
      </div>
    </button>
  )
}

export function GatewayPage({ data, agoSec, error, onOpenSession }: Props) {
  const { t } = useLang()

  if (error && !data) {
    return (
      <>
        <PageHead title={t.gateway} agoSec={agoSec} />
        <p className="text-[var(--bad)]">{error}</p>
      </>
    )
  }
  if (!data) {
    return (
      <>
        <PageHead title={t.gateway} agoSec={agoSec} />
        <p className="text-[var(--ink3)]">…</p>
      </>
    )
  }

  const sessions = data.sessions || []

  return (
    <>
      <PageHead title={t.gateway} home={data.home} agoSec={agoSec} />
      <p className="mb-3.5 text-[12.5px] text-[var(--ink2)]">{t.gatewayIntro}</p>
      {sessions.length ? (
        sessions.map((s) => (
          <SessionCard
            key={s.id}
            session={s}
            active={s.id === data.current_session}
            onOpen={onOpenSession}
          />
        ))
      ) : (
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
          {t.noConversations}
        </div>
      )}
    </>
  )
}
