import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'
import { stripToolsAnnotation } from '@/lib/format'
import type {
  ChatMeta,
  DashboardData,
  GateDecision,
  SessionHistoryMessage,
  StreamEvent,
  ToolCallRow,
} from '@/lib/types'

export type ChatUserMessage = {
  role: 'user'
  text: string
}

export type ChatAssistantMessage = {
  role: 'assistant'
  reply: string
  pending?: boolean
  stream?: string
  started?: number
  gate?: GateDecision | null
  tools?: ToolCallRow[]
  iterations?: number
  latency_ms?: number
  model?: string
  consolidation?: { new_facts?: number } | null
  llmNote?: string
  historical?: boolean
  error?: string
}

export type ChatMessage = ChatUserMessage | ChatAssistantMessage

function histItem(m: SessionHistoryMessage): ChatMessage {
  if (m.role === 'user') {
    return { role: 'user', text: m.content }
  }
  const meta = m.meta
  if (meta) {
    const tools = Array.isArray(meta.tools)
      ? meta.tools.map((t) =>
          typeof t === 'string' ? ({ tool: t } as ToolCallRow) : (t as ToolCallRow),
        )
      : undefined
    return {
      role: 'assistant',
      reply: m.content,
      gate: (meta.gate as GateDecision | null | undefined) ?? null,
      tools,
      iterations: meta.iterations,
      latency_ms: meta.latency_ms,
      model: meta.model,
    }
  }
  return {
    role: 'assistant',
    reply: stripToolsAnnotation(m.content),
    historical: true,
  }
}

function applyStreamEvent(
  pending: ChatAssistantMessage,
  ev: StreamEvent,
): ChatAssistantMessage {
  if (ev.kind === 'gate') {
    return {
      ...pending,
      gate: { decision: ev.decision, reason: ev.reason },
    }
  }
  if (ev.kind === 'text') {
    return {
      ...pending,
      stream: (pending.stream || '') + (ev.delta || ''),
    }
  }
  if (ev.kind === 'tool') {
    const tools = [...(pending.tools || [])]
    const output = ev.output || ''
    tools.push({
      tool: ev.tool || 'tool',
      args: ev.args,
      output,
      status: output.toLowerCase().startsWith('error') ? 'error' : 'ok',
      summary: output.split('. ')[0]?.slice(0, 120),
    })
    return { ...pending, tools, stream: '' }
  }
  if (ev.kind === 'llm') {
    const iter = typeof ev.iteration === 'number' ? ev.iteration : undefined
    return {
      ...pending,
      llmNote: iter != null ? `llm · iter ${iter}` : 'llm',
      iterations: iter ?? pending.iterations,
    }
  }
  if (ev.kind === 'consolidation') {
    return {
      ...pending,
      consolidation: { new_facts: ev.new_facts },
    }
  }
  if (ev.kind === 'done') {
    if (ev.error) {
      return {
        ...pending,
        pending: false,
        stream: '',
        reply: `Error: ${ev.error}`,
        error: ev.error,
      }
    }
    return {
      ...pending,
      pending: false,
      stream: '',
      reply: ev.reply || pending.stream || '',
      gate: ev.gate ?? pending.gate,
      tools: ev.tools ?? pending.tools,
      consolidation: ev.consolidation ?? pending.consolidation,
      iterations: ev.iterations ?? pending.iterations,
      latency_ms: ev.latency_ms ?? pending.latency_ms,
      model: ev.model ?? pending.model,
    }
  }
  return pending
}

export function useChatStream(
  data: DashboardData | null,
  onDone: () => void,
) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const restored = useRef(false)
  const onDoneRef = useRef(onDone)
  onDoneRef.current = onDone

  const loadThread = useCallback(
    async (
      id: string,
      mode: 'history' | 'switch' = 'history',
      opts: { setSession?: boolean } = {},
    ) => {
      const res = await api.session({
        action: mode,
        session_id: id,
      })
      if (res.error) throw new Error(res.error)
      const history = (res.history || []).map(histItem)
      setMessages(history)
      if (opts.setSession !== false) {
        setSessionId(res.session_id || id)
      }
    },
    [],
  )

  useEffect(() => {
    if (restored.current || !data?.current_session) return
    if (messages.length > 0) {
      restored.current = true
      return
    }
    restored.current = true
    void loadThread(data.current_session, 'history', { setSession: true }).catch(
      () => {
        // empty dock is fine if history fails
      },
    )
  }, [data, loadThread, messages.length])

  useEffect(() => {
    if (data?.current_session && !sessionId) {
      setSessionId(data.current_session)
    }
  }, [data?.current_session, sessionId])

  const newChat = useCallback(async () => {
    const res = await api.session({ action: 'new' })
    if (res.error) throw new Error(res.error)
    setMessages([])
    setSessionId(res.session_id || null)
    onDoneRef.current()
  }, [])

  const switchSession = useCallback(
    async (id: string) => {
      await loadThread(id, 'switch', { setSession: true })
      onDoneRef.current()
    },
    [loadThread],
  )

  const viewAllHistory = useCallback(() => {
    if (!data) return
    const rows: ChatMessage[] = []
    for (const m of data.chat_log || []) {
      let meta: ChatMeta | null = null
      if (typeof m.meta === 'string' && m.meta) {
        try {
          meta = JSON.parse(m.meta) as ChatMeta
        } catch {
          meta = null
        }
      } else if (m.meta && typeof m.meta === 'object') {
        meta = m.meta
      }
      rows.push(histItem({ role: m.role, content: m.content, meta }))
    }
    setMessages(rows)
    setSessionId('__all__')
  }, [data])

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || sending) return
      setSending(true)
      const pending: ChatAssistantMessage = {
        role: 'assistant',
        reply: '',
        pending: true,
        stream: '',
        started: Date.now(),
        tools: [],
      }
      setMessages((prev) => [...prev, { role: 'user', text: trimmed }, pending])
      try {
        for await (const ev of api.chatStream(trimmed, {
          sessionId: sessionId && sessionId !== '__all__' ? sessionId : undefined,
        })) {
          setMessages((prev) => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (!last || last.role !== 'assistant' || !last.pending) return prev
            next[next.length - 1] = applyStreamEvent(last, ev)
            return next
          })
        }
        setMessages((prev) => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last && last.role === 'assistant' && last.pending) {
            next[next.length - 1] = {
              ...last,
              pending: false,
              reply: last.stream || last.reply || '',
              stream: '',
            }
          }
          return next
        })
        onDoneRef.current()
      } catch (err) {
        const message = err instanceof Error ? err.message : 'stream failed'
        setMessages((prev) => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last && last.role === 'assistant') {
            next[next.length - 1] = {
              ...last,
              pending: false,
              reply: `Error: ${message}`,
              error: message,
            }
          }
          return next
        })
      } finally {
        setSending(false)
      }
    },
    [sending, sessionId],
  )

  return {
    messages,
    sessionId,
    sending,
    newChat,
    switchSession,
    viewAllHistory,
    send,
  }
}
