import { Link, useLocation } from 'react-router-dom'
import { RevealLink } from '@/components/layout/RevealLink'
import { Subtabs } from '@/components/layout/Subtabs'
import { PageHead } from '@/components/layout/PageHead'
import { useLang } from '@/hooks/useLang'
import type { DashboardData, ToolsInfo } from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  data: DashboardData | null
  agoSec: number | null
  error?: string | null
}

type CatalogItem = { name: string; description?: string; source?: string }

const SOURCE_GROUPS: { key: string; label: (t: ReturnType<typeof useLang>['t']) => string }[] = [
  { key: 'flagship', label: (t) => t.toolsFlagship },
  { key: 'web', label: (t) => t.toolsWeb },
  { key: 'self-management', label: (t) => t.toolsSelfMgmt },
  { key: 'mcp', label: (t) => t.toolsMcpGroup },
  { key: 'experimental', label: (t) => t.toolsExperimental },
  { key: 'other', label: (t) => t.toolsOther },
]

function useToolsSub(): string {
  const { pathname } = useLocation()
  const parts = pathname.split('/').filter(Boolean)
  return parts[1] || 'available'
}

function ToolCard({ item }: { item: CatalogItem }) {
  return (
    <div className="mb-2 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3">
      <div className="font-semibold" dir="ltr">
        {item.name}
        {item.source ? (
          <span className="ms-2 rounded px-1.5 py-px text-[10px] font-semibold uppercase bg-[var(--bg)] text-[var(--ink2)]">
            {item.source}
          </span>
        ) : null}
      </div>
      <div className="mt-1 text-[12.5px] text-[var(--ink2)]" dir="auto">
        {item.description}
      </div>
    </div>
  )
}

function ToolsAvailable({ tools }: { tools: ToolsInfo }) {
  const { t } = useLang()
  const catalog = (tools.catalog || []) as CatalogItem[]
  const planned = (tools.planned || []) as CatalogItem[]

  return (
    <>
      <p className="mb-3 text-[12.5px] text-[var(--ink2)]">
        {t.toolsAvailableIntro}{' '}
        <Link to="/tools/mcp" className="text-[var(--accent)] underline">
          MCP
        </Link>
        .
      </p>
      {SOURCE_GROUPS.map(({ key, label }) => {
        const items = catalog.filter((c) => c.source === key)
        if (!items.length) return null
        return (
          <section key={key} className="mb-5">
            <h2 className="mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
              {label(t)}
            </h2>
            {items.map((item) => (
              <ToolCard key={item.name} item={item} />
            ))}
          </section>
        )
      })}
      {planned.length ? (
        <section className="mb-5">
          <h2 className="mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
            {t.toolsComingSoon}
          </h2>
          {planned.map((item) => (
            <div
              key={item.name}
              className="mb-2 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 opacity-70"
            >
              <div className="font-semibold" dir="ltr">
                {item.name}
                <span className="ms-2 rounded px-1.5 py-px text-[10px] font-semibold uppercase bg-[var(--bg)] text-[var(--ink3)]">
                  soon
                </span>
              </div>
              <div className="mt-1 text-[12.5px] text-[var(--ink2)]" dir="auto">
                {item.description}
              </div>
            </div>
          ))}
        </section>
      ) : null}
    </>
  )
}

function ToolsResults({ data }: { data: DashboardData }) {
  const { t } = useLang()
  return (
    <>
      <p className="mb-3 text-[12.5px] text-[var(--ink2)]">{t.toolsResultsIntro}</p>
      <h2 className="mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.calendarEvents}
      </h2>
      {data.calendar.length ? (
        <div className="mb-4 overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)]">
          <table className="w-full border-collapse text-[13px]">
            <thead className="sticky top-0 bg-[var(--panel)]">
              <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                <th className="border-b border-[var(--line)] px-3 py-2">event</th>
                <th className="border-b border-[var(--line)] px-3 py-2">start</th>
                <th className="border-b border-[var(--line)] px-3 py-2">end</th>
                <th className="border-b border-[var(--line)] px-3 py-2">with</th>
              </tr>
            </thead>
            <tbody>
              {data.calendar.map((e, i) => (
                <tr key={`${e.title}-${i}`}>
                  <td className="border-b border-[var(--line)] px-3 py-2" dir="auto">
                    {e.title}
                  </td>
                  <td className="border-b border-[var(--line)] px-3 py-2 text-[11.5px] text-[var(--ink3)]" dir="ltr">
                    {e.start}
                  </td>
                  <td className="border-b border-[var(--line)] px-3 py-2 text-[11.5px] text-[var(--ink3)]" dir="ltr">
                    {e.end}
                  </td>
                  <td className="border-b border-[var(--line)] px-3 py-2" dir="auto">
                    {e.attendees}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="mb-4 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
          {t.noEvents}
        </div>
      )}
      <p className="mb-4 text-[11.5px] text-[var(--ink3)]" dir="ltr">
        {t.alsoWrittenTo}{' '}
        <RevealLink path="calendar.ics">calendar.ics</RevealLink>
      </p>
      <h2 className="mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.outboxTitle}{' '}
        <RevealLink path="outbox" className="text-[11px] font-normal normal-case tracking-normal">
          {t.openOutbox}
        </RevealLink>
      </h2>
      {data.outbox.length ? (
        data.outbox.map((o) => (
          <div
            key={o.name}
            className="mb-2 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3"
          >
            <div className="font-semibold" dir="ltr">
              {o.name}
            </div>
            <div className="mt-1 text-[12.5px] text-[var(--ink2)]" dir="auto">
              {o.text}
            </div>
          </div>
        ))
      ) : (
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
          {t.noOutbox}
        </div>
      )}
    </>
  )
}

function ToolsMcp({ tools, home }: { tools: ToolsInfo; home: string }) {
  const { t } = useLang()
  const m = tools.mcp || {}
  const configured = m.configured
  const live = m.live
  const servers = m.servers || []

  return (
    <>
      <div
        className={cn(
          'mb-4 rounded-lg border px-4 py-3',
          live ? 'border-[var(--good)]' : 'border-[var(--line2)]',
        )}
      >
        <b>
          {t.mcpTitle}
          {live ? t.mcpConnected : configured ? t.mcpConfigured : t.mcpNotSetup}
        </b>
        <p className="mt-1 text-[12.5px] text-[var(--ink2)]">{t.mcpIntro}</p>
        {configured ? (
          <p className="mt-2 text-[12px]" dir="ltr">
            {t.mcpServers}: {servers.map((s) => (
              <code key={s} className="me-2">
                {s}
              </code>
            ))}
            {!live ? ` — ${t.mcpStartChat}` : null}
          </p>
        ) : null}
      </div>
      <h2 className="mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.mcpConnectTitle}
      </h2>
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-[12.5px]">
        <p className="text-[var(--ink2)]" dir="ltr">
          1 — {t.mcpStep1}
        </p>
        <p className="mt-1.5 text-[var(--ink2)]" dir="ltr">
          2 — {t.mcpStep2}{' '}
          <RevealLink path="">.yar/mcp.json</RevealLink>:
        </p>
        <pre
          className="mt-2 overflow-x-auto font-mono text-[11.5px] text-[var(--ink2)] whitespace-pre-wrap"
          dir="ltr"
        >{`{"servers": [
  {"name": "fs", "command": "npx",
   "args": ["-y", "@modelcontextprotocol/server-filesystem", "${home}"]}
]}`}</pre>
        <p className="mt-2 text-[var(--ink2)]">
          3 — {t.mcpStep3}{' '}
          <Link to="/tools/available" className="text-[var(--accent)] underline">
            {t.subAvailable}
          </Link>
          .
        </p>
      </div>
    </>
  )
}

export function ToolsPage({ data, agoSec, error }: Props) {
  const { t } = useLang()
  const sub = useToolsSub()

  if (error && !data) {
    return (
      <>
        <PageHead title={t.tools} agoSec={agoSec} />
        <p className="text-[var(--bad)]">{error}</p>
      </>
    )
  }
  if (!data) {
    return (
      <>
        <PageHead title={t.tools} agoSec={agoSec} />
        <p className="text-[var(--ink3)]">…</p>
      </>
    )
  }

  const tools = data.tools || {}
  const catalogLen = (tools.catalog || []).length
  const mcpCount = tools.mcp?.servers?.length || null

  const tabs = [
    { key: 'available', label: t.subAvailable, count: catalogLen },
    { key: 'results', label: t.subResults },
    { key: 'mcp', label: t.subMcp, count: mcpCount },
  ]

  return (
    <>
      <PageHead title={t.tools} home={data.home} agoSec={agoSec} />
      <Subtabs base="/tools" tabs={tabs} active={sub} />
      {sub === 'results' ? (
        <ToolsResults data={data} />
      ) : sub === 'mcp' ? (
        <ToolsMcp tools={tools} home={data.home} />
      ) : (
        <ToolsAvailable tools={tools} />
      )}
    </>
  )
}
