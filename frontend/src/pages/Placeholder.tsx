import { PageHead } from '@/components/layout/PageHead'
import { Button } from '@/components/ui/button'
import { useLang } from '@/hooks/useLang'
import type { Copy } from '@/lib/i18n'

type Props = {
  titleKey: keyof Pick<
    Copy,
    | 'gateway'
    | 'loop'
    | 'memory'
    | 'tools'
    | 'database'
    | 'ops'
    | 'compare'
    | 'settings'
  >
  home?: string
  agoSec?: number | null
}

/** Placeholder for routes landing in issue 16. Settings already exposes the language toggle. */
export function PlaceholderPage({ titleKey, home, agoSec }: Props) {
  const { t, toggleLang } = useLang()
  return (
    <>
      <PageHead title={t[titleKey]} home={home} agoSec={agoSec} />
      <p className="mb-4 text-[var(--ink3)]">{t.comingSoon}</p>
      {titleKey === 'settings' ? (
        <Button type="button" variant="outline" size="sm" onClick={toggleLang}>
          {t.langToggle}
        </Button>
      ) : null}
    </>
  )
}
