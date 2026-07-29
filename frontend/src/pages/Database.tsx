import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { RevealLink } from '@/components/layout/RevealLink'
import { Subtabs } from '@/components/layout/Subtabs'
import { PageHead } from '@/components/layout/PageHead'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useEditing } from '@/hooks/useEditing'
import { useLang } from '@/hooks/useLang'
import { api } from '@/lib/api'
import type { DashboardData, DbTableInfo } from '@/lib/types'

type Props = {
  data: DashboardData | null
  agoSec: number | null
  error?: string | null
}

const DB_DESC: Record<string, string> = {
  calendar_events: 'events the create_event tool wrote (the flagship task)',
  facts: 'semantic memory — durable facts (Memory · Semantic)',
  episodes: 'episodic memory — dated summaries (Memory · Episodic)',
  chat_log: 'every message, tagged by session_id — consolidation reads from here',
}

const QUERY_EXAMPLES = [
  'SELECT role, content FROM chat_log ORDER BY id DESC LIMIT 10',
  'SELECT subject, content FROM facts',
  'SELECT session_id, COUNT(*) FROM chat_log GROUP BY session_id',
]

function useDbSub(): string {
  const { pathname } = useLocation()
  const parts = pathname.split('/').filter(Boolean)
  return parts[1] || 'overview'
}

function DbTableView({ table }: { table: DbTableInfo }) {
  if (!table.sample.length) {
    return (
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
        empty — no rows yet
      </div>
    )
  }
  return (
    <>
      <div className="max-h-[480px] overflow-auto rounded-lg border border-[var(--line)]">
        <table className="w-full border-collapse text-[13px]">
          <thead className="sticky top-0 bg-[var(--panel)]">
            <tr>
              {table.columns.map((c) => (
                <th
                  key={c}
                  className="border-b border-[var(--line)] px-3 py-2 text-start font-semibold text-[var(--accent)]"
                  dir="ltr"
                >
                  {c}
                  {table.types[c] ? (
                    <small className="ms-1 block font-normal text-[var(--ink3)]">
                      {table.types[c].toLowerCase()}
                    </small>
                  ) : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.sample.map((row, ri) => (
              <tr key={ri}>
                {table.columns.map((c) => (
                  <td
                    key={c}
                    className="border-b border-[var(--line)] px-3 py-1.5 font-mono text-[12px] text-[var(--ink2)]"
                    dir="auto"
                  >
                    {String(row[c] ?? '').slice(0, 120)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-1.5 text-[11.5px] text-[var(--ink3)]" dir="ltr">
        showing {table.sample.length} of {table.count} row{table.count === 1 ? '' : 's'} (newest
        first)
      </p>
    </>
  )
}

function QueryConsole() {
  const { t } = useLang()
  const { markEditing } = useEditing()
  const [sql, setSql] = useState(QUERY_EXAMPLES[0]!)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<{
    columns?: string[]
    rows?: string[][]
    error?: string
  } | null>(null)

  const run = async (query: string) => {
    setSql(query)
    markEditing()
    setRunning(true)
    setResult(null)
    try {
      const r = await api.query({ sql: query })
      setResult(r)
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      <p className="mb-2.5 text-[12.5px] text-[var(--ink2)]">{t.queryIntro}</p>
      <Textarea
        id="sqlbox"
        className="min-h-[100px] font-mono text-[12.5px]"
        dir="ltr"
        spellCheck={false}
        value={sql}
        onFocus={markEditing}
        onChange={(e) => {
          setSql(e.target.value)
          markEditing()
        }}
      />
      <div className="my-2 flex flex-wrap items-center gap-2">
        <Button type="button" size="sm" disabled={running} onClick={() => void run(sql)}>
          {t.run}
        </Button>
        <span className="text-[11.5px] text-[var(--ink3)]">
          {t.tryExamples}:{' '}
          {QUERY_EXAMPLES.map((q, i) => (
            <span key={q}>
              {i > 0 ? ' · ' : null}
              <button
                type="button"
                className="cursor-pointer border-0 bg-transparent p-0 font-mono text-[11px] text-[var(--accent)] underline"
                dir="ltr"
                onClick={() => void run(q)}
              >
                {q}
              </button>
            </span>
          ))}
        </span>
      </div>
      {running ? (
        <p className="text-[11.5px] text-[var(--ink3)]">{t.running}</p>
      ) : result?.error ? (
        <div className="rounded-lg border border-[var(--bad)] bg-[var(--bad-soft)] px-4 py-3 text-[var(--bad)]" dir="ltr">
          {result.error}
        </div>
      ) : result?.rows?.length ? (
        <>
          <div className="max-h-[480px] overflow-auto rounded-lg border border-[var(--line)]">
            <table className="w-full border-collapse text-[13px]">
              <thead className="sticky top-0 bg-[var(--panel)]">
                <tr>
                  {(result.columns || []).map((c) => (
                    <th
                      key={c}
                      className="border-b border-[var(--line)] px-3 py-2 text-start font-semibold text-[var(--accent)]"
                      dir="ltr"
                    >
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => (
                      <td
                        key={ci}
                        className="border-b border-[var(--line)] px-3 py-1.5 font-mono text-[12px]"
                        dir="auto"
                      >
                        {String(cell).slice(0, 120)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-1.5 text-[11.5px] text-[var(--ink3)]" dir="ltr">
            {result.rows.length} row(s)
          </p>
        </>
      ) : result ? (
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
          0 rows
        </div>
      ) : null}
    </>
  )
}

export function DatabasePage({ data, agoSec, error }: Props) {
  const { t } = useLang()
  const sub = useDbSub()

  if (error && !data) {
    return (
      <>
        <PageHead title={t.database} agoSec={agoSec} />
        <p className="text-[var(--bad)]">{error}</p>
      </>
    )
  }
  if (!data) {
    return (
      <>
        <PageHead title={t.database} agoSec={agoSec} />
        <p className="text-[var(--ink3)]">…</p>
      </>
    )
  }

  const db = data.db
  const tables = db.tables || []
  const tabs = [
    { key: 'overview', label: t.subOverview },
    ...tables.map((tbl) => ({ key: tbl.name, label: tbl.name, count: tbl.count })),
    { key: 'query', label: t.subQuery },
  ]

  let body: React.ReactNode = null

  if (sub === 'query') {
    body = <QueryConsole />
  } else if (sub !== 'overview') {
    const table = tables.find((x) => x.name === sub)
    body = table ? (
      <>
        {DB_DESC[table.name] ? (
          <p className="mb-2.5 text-[12.5px] text-[var(--ink2)]">{DB_DESC[table.name]}</p>
        ) : null}
        <DbTableView table={table} />
      </>
    ) : (
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
        no such table
      </div>
    )
  } else {
    const kb = (db.size / 1024).toFixed(1)
    body = (
      <>
        <div className="mb-4 rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)] px-4 py-3 text-[12.5px]">
          <b>{t.dbVsMemoryTitle}</b>
          <p className="mt-1 text-[var(--ink2)]">
            {t.dbVsMemoryBody}{' '}
            <Link to="/memory" className="text-[var(--accent)] underline">
              {t.memory}
            </Link>
            {t.dbVsMemoryBody2}
          </p>
        </div>
        <div className="mb-4 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3">
          <div className="break-all font-mono text-[12.5px]" dir="ltr">
            {db.path}
          </div>
          <p className="mt-1 text-[11.5px] text-[var(--ink3)]" dir="ltr">
            {kb} KB on disk · SQLite + FTS5 · open:{' '}
            <code>sqlite3 .yar/state.db</code>
          </p>
          <p className="mt-2 text-[11.5px] text-[var(--ink3)]" dir="ltr">
            <RevealLink path="state.db">state.db</RevealLink> ·{' '}
            <RevealLink path="">.yar/</RevealLink>
          </p>
        </div>
        <h2 className="mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
          {t.tablesTitle}
        </h2>
        <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)]">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                <th className="px-3 py-2">table</th>
                <th className="px-3 py-2">rows</th>
                <th className="px-3 py-2">what it holds</th>
              </tr>
            </thead>
            <tbody>
              {tables.map((tbl) => (
                <tr key={tbl.name}>
                  <td className="border-t border-[var(--line)] px-3 py-2">
                    <Link
                      to={`/database/${tbl.name}`}
                      className="font-mono text-[var(--accent)] underline"
                      dir="ltr"
                    >
                      {tbl.name}
                    </Link>
                  </td>
                  <td
                    className="border-t border-[var(--line)] px-3 py-2 text-[11.5px] text-[var(--ink3)] tabular-nums"
                    dir="ltr"
                  >
                    {tbl.count}
                  </td>
                  <td className="border-t border-[var(--line)] px-3 py-2 text-[11.5px] text-[var(--ink3)]">
                    {DB_DESC[tbl.name] || ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
          {t.ftsTitle}
        </h2>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-[12.5px] text-[var(--ink2)]">
          {t.ftsBody}
          <p className="mt-2 font-mono text-[11px] text-[var(--ink3)]" dir="ltr">
            {db.all_tables.map((tbl) => (
              <code key={tbl} className="me-2">
                {tbl}
              </code>
            ))}
          </p>
        </div>
      </>
    )
  }

  return (
    <>
      <PageHead title={t.database} home={data.home} agoSec={agoSec} />
      <Subtabs base="/database" tabs={tabs} active={sub} />
      {body}
    </>
  )
}
