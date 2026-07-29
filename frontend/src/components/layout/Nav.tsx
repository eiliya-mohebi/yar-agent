import { NavLink } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { CollapseStart } from '@/components/layout/Chevrons'
import { useLang } from '@/hooks/useLang'
import type { DashboardData } from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  data: DashboardData | null
  onCollapse: () => void
}

type NavItem = {
  to: string
  labelKey:
    | 'overview'
    | 'gateway'
    | 'loop'
    | 'memory'
    | 'tools'
    | 'database'
    | 'ops'
    | 'compare'
    | 'settings'
  badge?: string
}

export function Nav({ data, onCollapse }: Props) {
  const { t, toggleLang } = useLang()
  const s = data?.stats
  const items: NavItem[] = [
    { to: '/overview', labelKey: 'overview' },
    {
      to: '/gateway',
      labelKey: 'gateway',
      badge: String((data?.chat_log || []).length || ''),
    },
    {
      to: '/loop',
      labelKey: 'loop',
      badge: s ? String(s.turns) : '',
    },
    {
      to: '/memory',
      labelKey: 'memory',
      badge: data
        ? String((data.facts?.length || 0) + (data.episodes?.length || 0))
        : '',
    },
    {
      to: '/tools',
      labelKey: 'tools',
      badge: data
        ? String((data.calendar?.length || 0) + (data.outbox?.length || 0))
        : '',
    },
    {
      to: '/database',
      labelKey: 'database',
      badge: data?.db?.all_tables?.length
        ? String(data.db.all_tables.length)
        : '',
    },
    {
      to: '/ops',
      labelKey: 'ops',
      badge: s?.tool_errors
        ? String(s.tool_errors)
        : data && !data.eval_report
          ? '!'
          : '',
    },
    { to: '/compare', labelKey: 'compare' },
    { to: '/settings', labelKey: 'settings' },
  ]

  return (
    <nav
      className="flex h-screen w-[var(--nav-w)] shrink-0 flex-col overflow-y-auto border-e border-[var(--line)] px-3 py-5"
      aria-label="Primary"
    >
      <div className="mb-1 flex items-start justify-between gap-2 px-2.5">
        <div>
          <div className="text-[15px] font-semibold">{t.brand}</div>
          <div className="mt-0.5 text-[11px] text-[var(--ink3)]">{t.brandSub}</div>
        </div>
        <button
          type="button"
          className="rounded px-1 text-xs text-[var(--ink3)] hover:text-[var(--ink)]"
          onClick={onCollapse}
          aria-label="Collapse nav"
        >
          <CollapseStart />
        </button>
      </div>
      <NavLink
        to="/settings"
        className="mb-2 block truncate px-2.5 font-mono text-[11px] text-[var(--ink3)] hover:text-[var(--accent)]"
        dir="ltr"
        title={data ? `${data.model}` : undefined}
      >
        {data ? data.model : '—'}
      </NavLink>

      <div className="px-2.5 pt-4 pb-1 text-[10.5px] font-medium tracking-[0.09em] text-[var(--ink3)] uppercase">
        {t.system}
      </div>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            cn(
              'mt-0.5 flex items-center justify-between rounded-md px-2.5 py-1.5 text-[13.5px] text-[var(--ink2)] no-underline hover:bg-[var(--panel)] hover:text-[var(--ink)]',
              isActive &&
                'bg-[var(--accent-soft)] font-medium text-[var(--accent)]',
            )
          }
        >
          <span>{t[item.labelKey]}</span>
          {item.badge ? (
            <span className="font-mono text-[11px] text-[var(--ink3)] tabular-nums" dir="ltr">
              {item.badge}
            </span>
          ) : null}
        </NavLink>
      ))}

      <div className="mt-auto px-1 pt-4">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="w-full"
          onClick={toggleLang}
        >
          {t.langToggle}
        </Button>
      </div>
    </nav>
  )
}
