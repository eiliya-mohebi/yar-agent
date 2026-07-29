import { useLocation } from 'react-router-dom'
import { CollapseEnd, CollapseStart } from '@/components/layout/Chevrons'
import { Dock } from '@/components/layout/Dock'
import { Nav } from '@/components/layout/Nav'
import { Resizer } from '@/components/layout/Resizer'
import { useChatStream } from '@/hooks/useChatStream'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useLang } from '@/hooks/useLang'
import { useLocalChrome } from '@/hooks/useLocalChrome'
import { OverviewPage } from '@/pages/Overview'
import { PlaceholderPage } from '@/pages/Placeholder'
import type { Copy } from '@/lib/i18n'

const PLACEHOLDER: Record<
  string,
  keyof Pick<
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
> = {
  '/gateway': 'gateway',
  '/loop': 'loop',
  '/memory': 'memory',
  '/tools': 'tools',
  '/database': 'database',
  '/ops': 'ops',
  '/compare': 'compare',
  '/settings': 'settings',
}

export function Shell() {
  const { data, error, refresh, agoSec } = useDashboardData()
  const chrome = useLocalChrome()
  const chat = useChatStream(data, refresh)
  const location = useLocation()
  const { t } = useLang()
  const segment = location.pathname.split('/').filter(Boolean)[0] || 'overview'
  const placeholderKey =
    segment === 'overview'
      ? undefined
      : PLACEHOLDER[`/${segment}` as keyof typeof PLACEHOLDER]

  return (
    <div className="flex h-screen overflow-hidden">
      {!chrome.navHidden ? (
        <>
          <Nav data={data} onCollapse={() => chrome.setNavHidden(true)} />
          <Resizer
            cssVar="--nav-w"
            fromEnd={false}
            min={150}
            max={380}
            onResize={chrome.setNavW}
          />
        </>
      ) : (
        <button
          type="button"
          className="fixed top-3 z-25 size-[34px] rounded-lg border border-[var(--line2)] bg-[var(--panel)] text-sm text-[var(--ink2)]"
          style={{ insetInlineStart: 12 }}
          onClick={() => chrome.setNavHidden(false)}
          aria-label="Open nav"
        >
          <CollapseEnd />
        </button>
      )}

      <main className="h-screen min-w-0 flex-1 overflow-y-auto px-10 pb-8">
        {segment === 'overview' ? (
          <OverviewPage data={data} agoSec={agoSec} error={error} />
        ) : placeholderKey ? (
          <PlaceholderPage
            titleKey={placeholderKey}
            home={data?.home}
            agoSec={agoSec}
          />
        ) : (
          <OverviewPage data={data} agoSec={agoSec} error={error} />
        )}
        {error && data ? (
          <p className="mt-4 text-[11px] text-[var(--bad)]" dir="ltr">
            poll: {error}
          </p>
        ) : null}
      </main>

      {!chrome.dockClosed ? (
        <>
          <Resizer
            cssVar="--dock-w"
            fromEnd
            min={260}
            max={680}
            onResize={chrome.setDockW}
          />
          <Dock
            data={data}
            messages={chat.messages}
            sending={chat.sending}
            showTele={chrome.showTele}
            onNewChat={() => void chat.newChat()}
            onSwitchSession={(id) => void chat.switchSession(id)}
            onViewAll={chat.viewAllHistory}
            onToggleTele={chrome.toggleTele}
            onSend={(text) => void chat.send(text)}
            onClose={() => chrome.setDockClosed(true)}
          />
        </>
      ) : (
        <button
          type="button"
          className="fixed top-3 z-25 rounded-lg border border-[var(--line2)] bg-[var(--panel)] px-2.5 py-1.5 text-sm text-[var(--ink2)]"
          style={{ insetInlineEnd: 12 }}
          onClick={() => chrome.setDockClosed(false)}
          aria-label="Open chat"
        >
          <CollapseStart /> {t.chat}
        </button>
      )}
    </div>
  )
}
