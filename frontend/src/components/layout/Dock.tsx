import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { Transcript } from '@/components/chat/Transcript'
import { CollapseEnd } from '@/components/layout/Chevrons'
import { ModelChip } from '@/components/models/ModelChip'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Textarea } from '@/components/ui/textarea'
import { useLang } from '@/hooks/useLang'
import type { ChatMessage } from '@/hooks/useChatStream'
import type { DashboardData } from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  data: DashboardData | null
  messages: ChatMessage[]
  sending: boolean
  showTele: boolean
  onNewChat: () => void
  onSwitchSession: (id: string) => void
  onViewAll: () => void
  onToggleTele: () => void
  onSend: (text: string) => void
  onClose: () => void
  onRefresh: () => Promise<void>
}

export function Dock({
  data,
  messages,
  sending,
  showTele,
  onNewChat,
  onSwitchSession,
  onViewAll,
  onToggleTele,
  onSend,
  onClose,
  onRefresh,
}: Props) {
  const { t } = useLang()
  const [draft, setDraft] = useState('')

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    const text = draft.trim()
    if (!text) return
    setDraft('')
    onSend(text)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <aside className="flex h-screen w-[var(--dock-w)] shrink-0 flex-col border-s border-[var(--line)] bg-[var(--bg)] px-3.5">
      <div className="flex items-center gap-2 border-b border-[var(--line)] py-3">
        <Button type="button" variant="outline" size="sm" onClick={() => void onNewChat()}>
          {t.newChat}
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger
            className="inline-flex h-7 items-center justify-center rounded-lg border border-border bg-background px-2.5 text-[0.8rem] font-medium hover:bg-muted"
          >
            {t.history}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="max-h-80 w-[300px] overflow-y-auto">
            <DropdownMenuLabel>{t.history}</DropdownMenuLabel>
            <DropdownMenuItem onClick={onViewAll}>{t.allMessages}</DropdownMenuItem>
            <DropdownMenuSeparator />
            {(data?.sessions || []).map((s) => (
              <DropdownMenuItem
                key={s.id}
                onClick={() => void onSwitchSession(s.id)}
                className="flex flex-col items-stretch gap-0.5"
              >
                <span className="truncate" dir="auto">
                  {s.title || s.id}
                </span>
                <span className="font-mono text-[10px] text-[var(--ink3)]" dir="ltr">
                  {s.messages ?? 0} · {s.last_at || ''}
                </span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className={cn(showTele && 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]')}
          onClick={onToggleTele}
        >
          {t.stats}
        </Button>
        <ModelChip
          data={data}
          onRefresh={onRefresh}
          className="ms-auto max-w-[160px]"
        />
        <button
          type="button"
          className="rounded px-1 text-xs text-[var(--ink3)] hover:text-[var(--ink)]"
          onClick={onClose}
          aria-label="Close chat"
        >
          <CollapseEnd />
        </button>
      </div>

      <Transcript messages={messages} />

      <form className="border-t border-[var(--line)] py-3" onSubmit={submit}>
        <Textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={t.messagePlaceholder}
          rows={3}
          dir="auto"
          className="mb-2 resize-none"
          disabled={sending}
        />
        <Button type="submit" disabled={sending || !draft.trim()} className="w-full">
          {t.send}
        </Button>
      </form>
    </aside>
  )
}
