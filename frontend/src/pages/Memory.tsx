import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { RevealLink } from '@/components/layout/RevealLink'
import { Subtabs } from '@/components/layout/Subtabs'
import { PageHead } from '@/components/layout/PageHead'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useEditing } from '@/hooks/useEditing'
import { useLang } from '@/hooks/useLang'
import { api } from '@/lib/api'
import type { DashboardData, FactRow, SkillRow, Stats } from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  data: DashboardData | null
  agoSec: number | null
  error?: string | null
  onRefresh?: () => Promise<void>
}

function useSubRoute(defaultKey: string): string {
  const { pathname } = useLocation()
  const parts = pathname.split('/').filter(Boolean)
  return parts[1] || defaultKey
}

function GateSplit({ s, t }: { s: Stats; t: ReturnType<typeof useLang>['t'] }) {
  const tot = s.gate_skips + s.gate_retrieves
  if (!tot) {
    return (
      <>
        <div className="mt-0.5 flex h-[26px] overflow-hidden rounded-md border border-[var(--line)]">
          <div className="flex w-full items-center justify-center bg-[var(--accent)] text-[11px] font-semibold text-white opacity-35" />
        </div>
        <div className="mt-1.5 text-[11.5px] text-[var(--ink3)]">{t.gateEmpty}</div>
      </>
    )
  }
  const skipPct = Math.round((s.gate_skips / tot) * 100)
  const retPct = 100 - skipPct
  return (
    <>
      <div className="mt-0.5 flex h-[26px] overflow-hidden rounded-md border border-[var(--line)]">
        <div
          className="flex min-w-0 items-center justify-center overflow-hidden bg-[var(--accent)] text-[11px] font-semibold whitespace-nowrap text-white"
          style={{ width: `${skipPct}%` }}
          dir="ltr"
        >
          {skipPct >= 14 ? `${s.gate_skips} ${t.gateSkipped}` : ''}
        </div>
        <div
          className="flex min-w-0 items-center justify-center overflow-hidden bg-[var(--warn)] text-[11px] font-semibold whitespace-nowrap text-white"
          style={{ width: `${retPct}%` }}
          dir="ltr"
        >
          {retPct >= 14 ? `${s.gate_retrieves} ${t.gateRetrieved}` : ''}
        </div>
      </div>
      <div className="mt-1.5 text-[11.5px] text-[var(--ink3)]">{t.gateCaption(skipPct)}</div>
    </>
  )
}

function FactRowEditor({
  fact,
  onRefresh,
}: {
  fact: FactRow
  onRefresh?: () => Promise<void>
}) {
  const { t } = useLang()
  const { markEditing, clearEditing } = useEditing()
  const [editing, setEditing] = useState(false)
  const [content, setContent] = useState(fact.content)

  useEffect(() => {
    if (!editing) setContent(fact.content)
  }, [fact.content, editing])

  const save = async () => {
    await api.memory({ action: 'update_fact', id: fact.id, content: content.trim() })
    setEditing(false)
    clearEditing()
    await onRefresh?.()
  }

  const del = async () => {
    if (!window.confirm(t.confirmDeleteMemory)) return
    await api.memory({ action: 'delete_fact', id: fact.id })
    clearEditing()
    await onRefresh?.()
  }

  return (
    <tr id={`fact-${fact.id}`}>
      <td className="px-2 py-1.5 align-top">
        <code className="text-[12px]" dir="ltr">
          {fact.subject}
        </code>
      </td>
      <td className="max-w-md px-2 py-1.5 align-top" dir="auto">
        {editing ? (
          <Textarea
            className="min-h-[60px] font-sans text-[13px]"
            value={content}
            dir="auto"
            onChange={(e) => {
              setContent(e.target.value)
              markEditing()
            }}
            onFocus={markEditing}
          />
        ) : (
          fact.content
        )}
      </td>
      <td className="px-2 py-1.5 align-top text-[11.5px] text-[var(--ink3)]" dir="ltr">
        {fact.source}
      </td>
      <td className="px-2 py-1.5 align-top whitespace-nowrap">
        {editing ? (
          <>
            <button
              type="button"
              className="cursor-pointer border-0 bg-transparent p-0 text-[var(--accent)] underline"
              onClick={() => void save()}
            >
              {t.save}
            </button>
            <span className="mx-1 text-[var(--ink3)]">·</span>
            <button
              type="button"
              className="cursor-pointer border-0 bg-transparent p-0 text-[var(--ink2)] underline"
              onClick={() => {
                setEditing(false)
                setContent(fact.content)
                clearEditing()
              }}
            >
              {t.cancel}
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className="cursor-pointer border-0 bg-transparent p-0 text-[var(--accent)] underline"
              onClick={() => {
                setEditing(true)
                markEditing()
              }}
            >
              {t.edit}
            </button>
            <span className="mx-1 text-[var(--ink3)]">·</span>
            <button
              type="button"
              className="cursor-pointer border-0 bg-transparent p-0 text-[var(--bad)] underline"
              onClick={() => void del()}
            >
              {t.delete}
            </button>
          </>
        )}
      </td>
    </tr>
  )
}

function SkillEditor({
  skill,
  index,
  onRefresh,
}: {
  skill: SkillRow
  index: number
  onRefresh?: () => Promise<void>
}) {
  const { t } = useLang()
  const { markEditing, clearEditing } = useEditing()
  const fullDefault = useMemo(
    () => `---\nname: ${skill.name}\ndescription: ${skill.description}\n---\n\n${skill.body}`,
    [skill.name, skill.description, skill.body],
  )
  const [content, setContent] = useState(fullDefault)
  const [dirty, setDirty] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (dirty) return
    setContent(fullDefault)
    setDirty(false)
  }, [fullDefault, dirty])

  const save = async () => {
    setMsg('')
    try {
      const r = await api.memory({ action: 'save_skill', path: skill.path, content })
      setMsg(r.error ? `${t.error}: ${r.error}` : t.savedLive)
      if (!r.error) {
        setDirty(false)
        clearEditing()
        await onRefresh?.()
      }
    } catch (err) {
      setMsg(`${t.error}: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  return (
    <div className="mb-3 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5">
      <div className="font-semibold" dir="ltr">
        <code>{skill.name}</code>
        <span className="ms-2 font-normal text-[var(--ink2)]" dir="auto">
          · {skill.description}
        </span>
        <span
          className={cn(
            'ms-2 rounded px-1.5 py-px text-[10px] font-semibold uppercase',
            skill.editable
              ? 'bg-[var(--good-soft)] text-[var(--good)]'
              : 'bg-[var(--bg)] text-[var(--ink3)]',
          )}
          dir="ltr"
        >
          {skill.editable ? 'home' : 'built-in'}
        </span>
      </div>
      <Textarea
        id={`sk-${index}`}
        className="mt-2 min-h-[150px] font-mono text-[12px]"
        dir="auto"
        spellCheck={false}
        value={content}
        onFocus={markEditing}
        onChange={(e) => {
          setContent(e.target.value)
          setDirty(true)
          markEditing()
        }}
      />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          disabled={skill.editable ? !dirty : false}
          onClick={() => void save()}
        >
          {t.saveSkill}
        </Button>
        <span className="text-[11.5px] text-[var(--ink3)]" dir="ltr">
          {skill.rel || `skills/${skill.name}/SKILL.md`}
        </span>
        {msg ? (
          <span className="text-[11.5px] text-[var(--ink2)]" dir="auto">
            {msg}
          </span>
        ) : null}
      </div>
    </div>
  )
}

function SoulEditor({
  soul,
  onRefresh,
}: {
  soul: string
  onRefresh?: () => Promise<void>
}) {
  const { t } = useLang()
  const { markEditing, clearEditing } = useEditing()
  const [content, setContent] = useState(soul)
  const [dirty, setDirty] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (dirty) return
    setContent(soul)
    setDirty(false)
  }, [soul, dirty])

  const save = async () => {
    const r = await api.memory({ action: 'save_soul', content })
    setMsg(r.error ? `${t.error}: ${r.error}` : t.savedLive)
    if (!r.error) {
      setDirty(false)
      clearEditing()
      await onRefresh?.()
    }
  }

  return (
    <>
      <p className="mb-3 text-[12.5px] text-[var(--ink2)]">{t.soulIntro}</p>
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5">
        <Textarea
          id="soul"
          className="min-h-[260px] font-mono text-[13px]"
          dir="auto"
          spellCheck={false}
          value={content}
          onFocus={markEditing}
          onChange={(e) => {
            setContent(e.target.value)
            setDirty(true)
            markEditing()
          }}
        />
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Button type="button" size="sm" disabled={!dirty} onClick={() => void save()}>
            {t.saveSoul}
          </Button>
          {msg ? (
            <span className="text-[11.5px] text-[var(--ink2)]" dir="auto">
              {msg}
            </span>
          ) : null}
        </div>
      </div>
      <p className="mt-2.5 text-[11.5px] text-[var(--ink3)]">
        <RevealLink path="SOUL.md">SOUL.md</RevealLink>
      </p>
    </>
  )
}

export function MemoryPage({ data, agoSec, error, onRefresh }: Props) {
  const { t } = useLang()
  const sub = useSubRoute('overview')

  const refresh = useCallback(async () => {
    await onRefresh?.()
  }, [onRefresh])

  if (error && !data) {
    return (
      <>
        <PageHead title={t.memory} agoSec={agoSec} />
        <p className="text-[var(--bad)]">{error}</p>
      </>
    )
  }
  if (!data) {
    return (
      <>
        <PageHead title={t.memory} agoSec={agoSec} />
        <p className="text-[var(--ink3)]">…</p>
      </>
    )
  }

  const tabs = [
    { key: 'overview', label: t.subOverview },
    { key: 'semantic', label: t.subSemantic, count: data.facts.length },
    { key: 'episodic', label: t.subEpisodic, count: data.episodes.length },
    { key: 'skills', label: t.subSkills, count: data.skills.length },
    { key: 'soul', label: t.subSoul },
    { key: 'consolidation', label: t.subConsolidation, count: data.chat_pending },
  ]

  const distilled = data.facts.filter((f) => f.source === 'consolidation')

  let body: ReactNode = null

  if (sub === 'semantic') {
    body = (
      <>
        <p className="mb-3 text-[12.5px] text-[var(--ink2)]">{t.semanticIntro}</p>
        {data.facts.length ? (
          <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)] px-2 py-1">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                  <th className="px-2 py-1.5">subject</th>
                  <th className="px-2 py-1.5">fact</th>
                  <th className="px-2 py-1.5">source</th>
                  <th className="px-2 py-1.5" />
                </tr>
              </thead>
              <tbody>
                {data.facts.map((f) => (
                  <FactRowEditor key={f.id} fact={f} onRefresh={refresh} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
            {t.noFacts}
          </div>
        )}
      </>
    )
  } else if (sub === 'episodic') {
    body = (
      <>
        <div className="mb-3 rounded-lg border border-[var(--line2)] bg-[var(--accent-soft)] px-4 py-3 text-[12.5px]">
          <b>{t.episodicWhyTitle}</b>{' '}
          <span className="text-[var(--ink2)]">{t.episodicWhyBody}</span>
        </div>
        {data.episodes.length ? (
          <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)] px-2 py-1">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                  <th className="px-2 py-1.5">date</th>
                  <th className="px-2 py-1.5">episode</th>
                  <th className="px-2 py-1.5" />
                </tr>
              </thead>
              <tbody>
                {data.episodes.map((e) => (
                  <tr key={e.id}>
                    <td className="px-2 py-1.5 align-top text-[11.5px] text-[var(--ink3)]" dir="ltr">
                      {e.happened_at}
                    </td>
                    <td className="px-2 py-1.5 align-top" dir="auto">
                      {e.summary}
                    </td>
                    <td className="px-2 py-1.5 align-top whitespace-nowrap">
                      <button
                        type="button"
                        className="cursor-pointer border-0 bg-transparent p-0 text-[var(--bad)] underline"
                        onClick={async () => {
                          if (!window.confirm(t.confirmDeleteMemory)) return
                          await api.memory({ action: 'delete_episode', id: e.id })
                          await refresh()
                        }}
                      >
                        {t.delete}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
            {t.noEpisodes}
          </div>
        )}
      </>
    )
  } else if (sub === 'skills') {
    body = (
      <>
        <p className="mb-3 text-[12.5px] text-[var(--ink2)]">{t.skillsIntro}</p>
        {data.skills.length ? (
          data.skills.map((sk, i) => (
            <SkillEditor key={sk.name} skill={sk} index={i} onRefresh={refresh} />
          ))
        ) : (
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
            {t.noSkills}
          </div>
        )}
      </>
    )
  } else if (sub === 'soul') {
    body = <SoulEditor soul={data.soul} onRefresh={refresh} />
  } else if (sub === 'consolidation') {
    body = (
      <>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-[12.5px]">
          <b>{t.consolidationHowTitle}</b>{' '}
          <span className="text-[var(--ink2)]">
            {t.consolidationHowBody(data.consolidate_every)}
          </span>
        </div>
        <div className="mt-3 grid grid-cols-[repeat(auto-fill,minmax(128px,1fr))] gap-2.5">
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3.5 py-3">
            <b className="block text-[19px] font-semibold tabular-nums" dir="ltr">
              {data.chat_pending}
            </b>
            <span className="text-[11.5px] text-[var(--ink2)]">{t.messagesQueued}</span>
          </div>
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3.5 py-3">
            <b className="block text-[19px] font-semibold tabular-nums" dir="ltr">
              {data.consolidate_every * 2}
            </b>
            <span className="text-[11.5px] text-[var(--ink2)]">{t.triggerThreshold}</span>
          </div>
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3.5 py-3">
            <b className="block text-[19px] font-semibold tabular-nums" dir="ltr">
              {distilled.length}
            </b>
            <span className="text-[11.5px] text-[var(--ink2)]">{t.factsFromConsolidation}</span>
          </div>
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3.5 py-3">
            <b className="block text-[19px] font-semibold tabular-nums" dir="ltr">
              {data.episodes.length}
            </b>
            <span className="text-[11.5px] text-[var(--ink2)]">{t.episodesTotal}</span>
          </div>
        </div>
        <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
          {t.distilledFacts}
        </h2>
        {distilled.length ? (
          <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)] px-2 py-1">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="text-start text-[11px] font-semibold tracking-wide text-[var(--ink2)] uppercase">
                  <th className="px-2 py-1.5">subject</th>
                  <th className="px-2 py-1.5">fact</th>
                  <th className="px-2 py-1.5">when</th>
                </tr>
              </thead>
              <tbody>
                {distilled.map((f) => (
                  <tr key={f.id}>
                    <td className="px-2 py-1.5 align-top">
                      <code dir="ltr">{f.subject}</code>
                    </td>
                    <td className="px-2 py-1.5 align-top" dir="auto">
                      {f.content}
                    </td>
                    <td className="px-2 py-1.5 align-top text-[11.5px] text-[var(--ink3)]" dir="ltr">
                      {(f.created_at || '').slice(0, 10)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5 text-[var(--ink3)]">
            {t.noFacts}
          </div>
        )}
      </>
    )
  } else {
    const pillars = [
      {
        title: t.subSemantic,
        sub: 'semantic',
        count: `${data.facts.length} ${t.facts}`,
        desc: t.pillarSemanticDesc,
      },
      {
        title: t.subEpisodic,
        sub: 'episodic',
        count: `${data.episodes.length} episodes`,
        desc: t.pillarEpisodicDesc,
      },
      {
        title: t.subSkills,
        sub: 'skills',
        count: `${data.skills.length} skills`,
        desc: t.pillarSkillsDesc,
      },
    ]
    body = (
      <>
        <div className="mb-4 rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)] px-4 py-3 text-[12.5px]">
          <b>{t.memoryVsDbTitle}</b>
          <p className="mt-1 text-[var(--ink2)]">
            {t.memoryVsDbBody}{' '}
            <Link to="/database" className="text-[var(--accent)] underline">
              {t.database}
            </Link>
            {t.memoryVsDbBody2}
          </p>
        </div>
        <h2 className="mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
          {t.threePillars}
        </h2>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-2.5">
          {pillars.map((p) => (
            <Link
              key={p.sub}
              to={`/memory/${p.sub}`}
              className="block rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3.5 py-3 no-underline transition-colors hover:border-[var(--line2)]"
            >
              <b className="block text-[var(--ink)]">
                {p.title}{' '}
                <span className="font-normal text-[var(--ink3)]">· {p.count}</span>
              </b>
              <span className="mt-1 block text-[12px] text-[var(--ink2)]">{p.desc}</span>
            </Link>
          ))}
        </div>
        <h2 className="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
          {t.gateHero}
        </h2>
        <GateSplit s={data.stats} t={t} />
        <p className="mt-2 text-[11.5px] text-[var(--ink3)]">{t.memoryGateNote}</p>
        <p className="mt-3.5 text-[11.5px] text-[var(--ink3)]" dir="ltr">
          {t.filesLabel}:{' '}
          <RevealLink path="state.db">state.db</RevealLink> ·{' '}
          <RevealLink path="MEMORY.md">MEMORY.md</RevealLink> ·{' '}
          <RevealLink path="SOUL.md">SOUL.md</RevealLink> ·{' '}
          <RevealLink path="skills">skills/</RevealLink>
        </p>
      </>
    )
  }

  return (
    <>
      <PageHead title={t.memory} home={data.home} agoSec={agoSec} />
      <Subtabs base="/memory" tabs={tabs} active={sub} />
      {body}
    </>
  )
}
