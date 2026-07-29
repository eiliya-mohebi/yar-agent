import { secs } from '@/lib/format'
import type { ChatAssistantMessage } from '@/hooks/useChatStream'
import { MarkdownText } from '@/components/chat/Markdown'
import { useLang } from '@/hooks/useLang'
import { cn } from '@/lib/utils'

function Stages({
  m,
  live,
}: {
  m: ChatAssistantMessage
  live: boolean
}) {
  const gateCls = live ? (m.gate ? 'done' : 'on') : 'done'
  const replyCls = live ? (m.stream ? 'on' : '') : 'done'
  const gateLabel = m.gate?.decision ? `gate · ${m.gate.decision}` : 'gate'
  return (
    <div className={cn('mb-1.5 flex flex-wrap gap-1.5', !live && 'tele')}>
      <Stage className={gateCls}>{gateLabel}</Stage>
      {m.llmNote ? <Stage className={live ? 'on' : 'done'}>{m.llmNote}</Stage> : null}
      {(m.tools || []).map((x, i) => (
        <Stage key={`${x.tool}-${i}`} className="done">{`tool · ${x.tool}`}</Stage>
      ))}
      {m.consolidation ? (
        <Stage className={live ? 'on' : 'done'}>
          {`consolidation · ${m.consolidation.new_facts ?? 0}`}
        </Stage>
      ) : null}
      <Stage className={replyCls}>reply</Stage>
    </div>
  )
}

function Stage({
  children,
  className,
}: {
  children: string
  className?: string
}) {
  return (
    <span
      className={cn(
        'rounded-full border border-[var(--line2)] px-2 py-0.5 font-mono text-[11px] text-[var(--ink3)]',
        className === 'on' && 'border-[var(--accent)] text-[var(--accent)]',
        className === 'done' && 'border-[var(--line)] text-[var(--ink2)]',
      )}
      dir="ltr"
    >
      {children}
    </span>
  )
}

function ToolRow({
  tool,
  status,
  summary,
  args,
  output,
}: {
  tool: string
  status?: string
  summary?: string
  args?: unknown
  output?: string
}) {
  return (
    <div
      className={cn(
        'mt-2 rounded-[7px] border border-[var(--line)] bg-[var(--bg)] px-2.5 py-2',
        status === 'error' && 'border-[var(--bad)] bg-[var(--bad-soft)]',
      )}
    >
      <div className="flex items-center gap-2 text-[12.5px]">
        <span
          className={cn(
            'size-[7px] shrink-0 rounded-full bg-[var(--good)]',
            status === 'error' && 'bg-[var(--bad)]',
            status === 'warn' && 'bg-[var(--warn)]',
          )}
        />
        <code className="font-mono text-[var(--ink)]" dir="ltr">
          {tool}
        </code>
        {summary ? (
          <span className="text-[var(--ink2)]" dir="auto">
            {summary}
          </span>
        ) : null}
      </div>
      {output !== undefined ? (
        <details className="mt-1.5">
          <summary className="cursor-pointer text-[11px] text-[var(--ink3)]">
            args &amp; raw output
          </summary>
          <pre
            className="mt-1.5 max-h-[180px] overflow-auto font-mono text-[11px] break-all whitespace-pre-wrap text-[var(--ink2)]"
            dir="ltr"
          >
            {`${tool}(${JSON.stringify(args ?? null, null, 1)})\n\n${output}`}
          </pre>
        </details>
      ) : null}
    </div>
  )
}

function TeleFooter({ m }: { m: ChatAssistantMessage }) {
  return (
    <div className="tele mt-2 font-mono text-[11.5px] text-[var(--ink3)] tabular-nums" dir="ltr">
      {secs(m.latency_ms)} · {m.iterations ?? '?'} iter
      {m.model ? ` · ${m.model}` : ''}
      {m.consolidation
        ? ` · consolidated ${m.consolidation.new_facts ?? 0} fact(s)`
        : ''}
    </div>
  )
}

export function ChatBubble({ text }: { text: string }) {
  return (
    <div
      className="ms-auto mb-2 max-w-[92%] rounded-[9px] bg-[var(--accent-soft)] px-3 py-2.5 text-[13.5px] text-[var(--ink)]"
      dir="auto"
    >
      {text}
    </div>
  )
}

export function StreamPending({ m }: { m: ChatAssistantMessage }) {
  const { t } = useLang()
  const elapsed = m.started ? Math.round((Date.now() - m.started) / 1000) : 0
  return (
    <div className="mb-2 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5">
      <Stages m={m} live />
      {m.gate?.reason ? (
        <div className="mb-1.5 text-[11.5px] text-[var(--ink3)]" dir="auto">
          {m.gate.reason}
        </div>
      ) : null}
      <div className="tele">
        {(m.tools || []).map((x, i) => (
          <ToolRow key={`${x.tool}-${i}`} {...x} />
        ))}
      </div>
      {m.stream ? (
        <div className="mt-2">
          <MarkdownText text={m.stream} />
          <span className="caret" />
        </div>
      ) : (
        <div className="text-[11.5px] text-[var(--ink3)]">
          {t.thinking}
          {m.started ? ` ${elapsed}s` : ''}
        </div>
      )}
    </div>
  )
}

export function AssistantCard({ m }: { m: ChatAssistantMessage }) {
  if (m.historical) {
    return (
      <div className="mb-2 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5">
        <MarkdownText text={m.reply} />
      </div>
    )
  }
  return (
    <div className="mb-2 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5">
      {m.gate ? (
        <>
          <Stages m={m} live={false} />
          <div className="tele mb-1.5 text-[11.5px] text-[var(--ink3)]" dir="auto">
            {m.gate.reason || ''}
          </div>
        </>
      ) : null}
      {(m.tools || []).length ? (
        <div className="tele">
          {(m.tools || []).map((x, i) => (
            <ToolRow key={`${x.tool}-${i}`} {...x} />
          ))}
        </div>
      ) : null}
      <div className="mt-2">
        <MarkdownText text={m.reply} />
      </div>
      <TeleFooter m={m} />
    </div>
  )
}
