import { useLang } from '@/hooks/useLang'

type Props = {
  title: string
  home?: string
  agoSec?: number | null
}

export function PageHead({ title, home, agoSec }: Props) {
  const { t } = useLang()
  return (
    <header className="sticky top-0 z-[6] mb-[18px] border-b border-[var(--line)] bg-[var(--bg)] pt-7 pb-2.5">
      <h1 className="mb-0.5 text-[17px] font-semibold">{title}</h1>
      <div className="text-xs text-[var(--ink3)]">
        <span className="inline-flex items-center gap-1.5">
          <span
            className="inline-block size-[7px] rounded-full bg-[var(--good)]"
            style={{ animation: 'pulse-dot 2s ease-in-out infinite' }}
          />
          {t.live}
        </span>
        {agoSec != null ? (
          <>
            {' · '}
            {t.updated}{' '}
            <span className="font-mono tabular-nums" dir="ltr">
              {agoSec}s
            </span>{' '}
            {t.ago}
          </>
        ) : null}
        {home ? (
          <>
            {' · '}
            <span className="font-mono" dir="ltr">
              {home}
            </span>
          </>
        ) : null}
      </div>
    </header>
  )
}
