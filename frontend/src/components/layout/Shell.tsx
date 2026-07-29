import { useEffect, useRef, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { CollapseEnd, CollapseStart } from '@/components/layout/Chevrons'
import { Dock } from '@/components/layout/Dock'
import { Nav } from '@/components/layout/Nav'
import { Resizer } from '@/components/layout/Resizer'
import { useChatStream } from '@/hooks/useChatStream'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useEditing } from '@/hooks/useEditing'
import { useLang } from '@/hooks/useLang'
import { useLocalChrome } from '@/hooks/useLocalChrome'
import { ComparePage } from '@/pages/Compare'
import { DatabasePage } from '@/pages/Database'
import { GatewayPage } from '@/pages/Gateway'
import { LoopPage } from '@/pages/Loop'
import { MemoryPage } from '@/pages/Memory'
import { OpsPage } from '@/pages/Ops'
import { OverviewPage } from '@/pages/Overview'
import { SettingsPage } from '@/pages/Settings'
import { ToolsPage } from '@/pages/Tools'

export function Shell() {
  const { data, error, refresh, agoSec } = useDashboardData()
  const chrome = useLocalChrome()
  const chat = useChatStream(data, refresh)
  const location = useLocation()
  const { t } = useLang()
  const { clearEditing } = useEditing()
  const mainRef = useRef<HTMLElement>(null)
  const pathRef = useRef(location.pathname)
  const segment = location.pathname.split('/').filter(Boolean)[0] || 'overview'

  // Clear edit lock + jump to top on real navigation (not 5s poll remounts).
  useEffect(() => {
    if (pathRef.current !== location.pathname) {
      pathRef.current = location.pathname
      clearEditing()
      if (mainRef.current) mainRef.current.scrollTop = 0
    }
  }, [location.pathname, clearEditing])

  // Same-route data refresh: preserve scroll (waku poll guard).
  const scrollY = useRef(0)
  useEffect(() => {
    const el = mainRef.current
    if (!el) return
    const onScroll = () => {
      scrollY.current = el.scrollTop
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])
  useEffect(() => {
    const el = mainRef.current
    if (!el || pathRef.current !== location.pathname) return
    el.scrollTop = scrollY.current
  }, [data, location.pathname])

  let page: ReactNode
  switch (segment) {
    case 'gateway':
      page = (
        <GatewayPage
          data={data}
          agoSec={agoSec}
          error={error}
          onOpenSession={(id) => {
            chrome.setDockClosed(false)
            void chat.switchSession(id)
          }}
        />
      )
      break
    case 'loop':
      page = <LoopPage data={data} agoSec={agoSec} error={error} />
      break
    case 'memory':
      page = (
        <MemoryPage data={data} agoSec={agoSec} error={error} onRefresh={refresh} />
      )
      break
    case 'tools':
      page = <ToolsPage data={data} agoSec={agoSec} error={error} />
      break
    case 'database':
      page = <DatabasePage data={data} agoSec={agoSec} error={error} />
      break
    case 'ops':
      page = <OpsPage data={data} agoSec={agoSec} error={error} />
      break
    case 'compare':
      page = (
        <ComparePage
          data={data}
          agoSec={agoSec}
          active
          onRefresh={refresh}
        />
      )
      break
    case 'settings':
      page = (
        <SettingsPage
          data={data}
          agoSec={agoSec}
          error={error}
          onRefresh={refresh}
        />
      )
      break
    default:
      page = <OverviewPage data={data} agoSec={agoSec} error={error} />
  }

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

      <main
        ref={mainRef}
        className="h-screen min-w-0 flex-1 overflow-y-auto px-10 pb-8"
      >
        {page}
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
            onRefresh={refresh}
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
