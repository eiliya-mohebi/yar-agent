import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

export type SubtabItem = {
  key: string
  label: string
  count?: number | null
}

type Props = {
  base: string
  tabs: SubtabItem[]
  active: string
}

export function Subtabs({ base, tabs, active }: Props) {
  return (
    <div className="mb-5 flex flex-wrap border-b border-[var(--line)]">
      {tabs.map((tab) => {
        const to = tab.key === 'overview' ? base : `${base}/${tab.key}`
        const isActive = active === tab.key
        return (
          <NavLink
            key={tab.key}
            to={to}
            end={tab.key === 'overview'}
            className={cn(
              'relative px-3 py-2 text-[12.5px] font-medium text-[var(--ink2)] no-underline transition-colors',
              isActive && 'text-[var(--accent)]',
            )}
          >
            {tab.label}
            {tab.count != null ? (
              <span
                className="ms-1.5 inline-block rounded-full bg-[var(--accent-soft)] px-1.5 py-px text-[10px] font-semibold tabular-nums text-[var(--accent)]"
                dir="ltr"
              >
                {tab.count}
              </span>
            ) : null}
            {isActive ? (
              <span className="absolute inset-x-0 bottom-0 h-0.5 bg-[var(--accent)]" />
            ) : null}
          </NavLink>
        )
      })}
    </div>
  )
}
