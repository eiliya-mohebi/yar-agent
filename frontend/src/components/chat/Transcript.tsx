import { useEffect, useRef } from 'react'
import {
  AssistantCard,
  ChatBubble,
  StreamPending,
} from '@/components/chat/ChatBubble'
import type { ChatMessage } from '@/hooks/useChatStream'
import { useLang } from '@/hooks/useLang'

export function Transcript({ messages }: { messages: ChatMessage[] }) {
  const { t } = useLang()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages])

  return (
    <div ref={ref} className="chatlog flex min-h-0 flex-1 flex-col overflow-y-auto py-2">
      {messages.length === 0 ? (
        <div className="px-1 py-1.5 text-[var(--ink3)]">{t.dockEmpty}</div>
      ) : (
        messages.map((m, i) => {
          if (m.role === 'user') {
            return <ChatBubble key={i} text={m.text} />
          }
          if (m.pending) {
            return <StreamPending key={i} m={m} />
          }
          return <AssistantCard key={i} m={m} />
        })
      )}
    </div>
  )
}
