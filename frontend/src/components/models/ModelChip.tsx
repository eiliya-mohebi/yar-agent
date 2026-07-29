import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { applyModel } from '@/lib/settings'
import type { DashboardData } from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  data: DashboardData | null
  onRefresh: () => Promise<void>
  className?: string
}

export function ModelChip({ data, onRefresh, className }: Props) {
  const [busy, setBusy] = useState(false)
  const current = data?.model ?? data?.settings.model ?? '…'
  const pinned = data?.settings.pinned ?? []

  const options = (() => {
    const ids: string[] = []
    const seen = new Set<string>()
    for (const p of pinned) {
      if (!seen.has(p.id)) {
        seen.add(p.id)
        ids.push(p.id)
      }
    }
    if (current && !seen.has(current)) ids.unshift(current)
    return ids
  })()

  const switchTo = async (id: string) => {
    if (id === current || busy) return
    setBusy(true)
    try {
      const r = await applyModel({ model: id })
      if (!r.error) await onRefresh()
    } finally {
      setBusy(false)
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className={cn('h-7 max-w-[220px] truncate font-mono text-[11.5px]', className)}
          dir="ltr"
          disabled={busy}
        >
          {current}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="max-h-[280px] overflow-y-auto">
        {options.map((id) => (
          <DropdownMenuItem
            key={id}
            className="font-mono text-[12px]"
            dir="ltr"
            disabled={id === current || busy}
            onClick={() => void switchTo(id)}
          >
            {id}
            {id === current ? ' · current' : ''}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
