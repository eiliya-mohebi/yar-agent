import { TurnCard } from '@/components/chat/TurnCard'
import { PageHead } from '@/components/layout/PageHead'
import { useLang } from '@/hooks/useLang'
import type { DashboardData } from '@/lib/types'

type Props = {
  data: DashboardData | null
  agoSec: number | null
  error?: string | null
}

export function LoopPage({ data, agoSec, error }: Props) {
  const { t } = useLang()

  if (error && !data) {
    return (
      <>
        <PageHead title={t.loop} agoSec={agoSec} />
        <p className="text-[var(--bad)]">{error}</p>
      </>
    )
  }
  if (!data) {
    return (
      <>
        <PageHead title={t.loop} agoSec={agoSec} />
        <p className="text-[var(--ink3)]">…</p>
      </>
    )
  }

  return (
    <>
      <PageHead title={t.loop} home={data.home} agoSec={agoSec} />
      {data.turns.length ? (
        data.turns.map((turn, i) => <TurnCard key={`${turn.ts}-${i}`} turn={turn} />)
      ) : (
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
          {t.noTurns}
        </div>
      )}
    </>
  )
}
