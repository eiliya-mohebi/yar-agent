import { useCallback, useEffect, useRef, useState } from 'react'
import { ResultCols } from '@/components/compare/ResultCols'
import { Scoreboard } from '@/components/compare/Scoreboard'
import { PageHead } from '@/components/layout/PageHead'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useEditing } from '@/hooks/useEditing'
import { useLang } from '@/hooks/useLang'
import { api } from '@/lib/api'
import {
  adaptHistResult,
  COMPARE_STORAGE_KEY,
  DEFAULT_COMPARE_MESSAGE,
  judgeModelOptions,
  modelFromSpec,
  setCompareRunning,
  toSpec,
  type BoardSort,
  type BoardSortKey,
  type SortMetric,
} from '@/lib/compare'
import type {
  CompareHistoryResponse,
  CompareResult,
  CompareStreamEvent,
  DashboardData,
} from '@/lib/types'
import { cn } from '@/lib/utils'

const POLL_MS = 5000

type SavedCompare = {
  message?: string
  order?: string[]
  results?: Record<string, CompareResult> | null
}

type Props = {
  data: DashboardData | null
  agoSec: number | null
  active: boolean
  onRefresh?: () => Promise<void>
}

function loadSaved(): SavedCompare | null {
  try {
    const raw = localStorage.getItem(COMPARE_STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as SavedCompare
  } catch {
    return null
  }
}

function saveCompare(state: {
  message: string
  order: string[] | null
  results: Record<string, CompareResult> | null
}) {
  try {
    localStorage.setItem(
      COMPARE_STORAGE_KEY,
      JSON.stringify({
        message: state.message,
        order: state.order,
        results: state.results,
      }),
    )
  } catch {
    // ignore quota errors
  }
}

function applyHistory(resp: CompareHistoryResponse) {
  return {
    history: resp.runs ?? [],
    aggregate: resp.aggregate ?? [],
  }
}

export function ComparePage({ data, agoSec, active, onRefresh }: Props) {
  const { t } = useLang()
  const { editing, markEditing, clearEditing } = useEditing()

  const saved = useRef(loadSaved())
  const pinned = data?.settings?.pinned ?? []
  const pinnedIds = pinned.map((p) => p.id)

  const [message, setMessage] = useState(
    () => saved.current?.message ?? DEFAULT_COMPARE_MESSAGE,
  )
  const [picked, setPicked] = useState<Set<string> | null>(() => {
    if (saved.current?.order?.length) {
      return new Set(saved.current.order.map((s) => modelFromSpec(s)))
    }
    return null
  })
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState<Record<string, CompareResult> | null>(
    () => saved.current?.results ?? null,
  )
  const [order, setOrder] = useState<string[] | null>(
    () =>
      saved.current?.order?.map((s) => modelFromSpec(s)) ??
      null,
  )
  const [sortBy, setSortBy] = useState<SortMetric>('latency')
  const [judge, setJudge] = useState(true)
  const [judgeModel, setJudgeModel] = useState(
    () => data?.settings?.small_model || 'gpt-4.1-mini',
  )
  const [history, setHistory] = useState<CompareHistoryResponse['runs']>([])
  const [aggregate, setAggregate] = useState<
    CompareHistoryResponse['aggregate']
  >([])
  const [boardSort, setBoardSort] = useState<BoardSort>({
    key: 'total_cost_usd',
    dir: 'asc',
  })
  const [grading, setGrading] = useState<{
    n?: number
    judge?: string
    done?: number
  } | null>(null)
  const [raceError, setRaceError] = useState<string | null>(null)
  const [regrading, setRegrading] = useState(false)
  const [catalogIds, setCatalogIds] = useState<string[]>([])
  const historyLoaded = useRef(false)

  const pickIds = (() => {
    const seen = new Set<string>()
    const out: string[] = []
    for (const id of [...pinnedIds, ...catalogIds]) {
      if (!id || seen.has(id)) continue
      seen.add(id)
      out.push(id)
    }
    return out
  })()

  const effectivePicked =
    picked ?? new Set(pinnedIds.length ? pinnedIds : pickIds.slice(0, 4))

  useEffect(() => {
    const sm = data?.settings?.small_model
    if (sm) {
      setJudgeModel((prev) => (prev === 'gpt-4.1-mini' ? sm : prev))
    }
  }, [data?.settings?.small_model])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const cat = await api.models()
        if (cancelled) return
        setCatalogIds((cat.models || []).map((m) => m.id).filter(Boolean))
      } catch {
        if (!cancelled) setCatalogIds([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const loadHistory = useCallback(async () => {
    try {
      const h = await api.compareHistory()
      const next = applyHistory(h)
      setHistory(next.history)
      setAggregate(next.aggregate)
      clearEditing()
    } catch {
      setHistory([])
      setAggregate([])
    }
  }, [clearEditing])

  useEffect(() => {
    if (!historyLoaded.current) {
      historyLoaded.current = true
      void loadHistory()
    }
  }, [loadHistory])

  useEffect(() => {
    if (!active || running || editing) return
    const id = window.setInterval(() => void loadHistory(), POLL_MS)
    return () => window.clearInterval(id)
  }, [active, running, editing, loadHistory])

  const toggleModel = (id: string) => {
    setPicked((prev) => {
      const base = prev ?? new Set(pinnedIds)
      const next = new Set(base)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
    clearEditing()
  }

  const setBoardSortKey = (key: BoardSortKey) => {
    setBoardSort((b) =>
      b.key === key
        ? { key, dir: b.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: 'asc' },
    )
    clearEditing()
  }

  const handleStreamEvent = (
    ev: CompareStreamEvent,
    R: Record<string, CompareResult>,
  ) => {
    const s = ev.spec
    if (ev.kind === 'start' && s) {
      R[s] = {
        spec: s,
        provider: ev.provider,
        model: ev.model,
        streaming: true,
        tools: [],
        gate: null,
      }
      return
    }
    if (ev.kind === 'gate' && s && R[s]) {
      R[s] = {
        ...R[s],
        gate: { decision: ev.decision, reason: ev.reason },
      }
      return
    }
    if (ev.kind === 'tool' && s && R[s]) {
      R[s] = {
        ...R[s],
        tools: [...(R[s].tools || []), { tool: ev.tool || '' }],
      }
      return
    }
    if (ev.kind === 'result' && s) {
      const row = ev as CompareResult & { kind?: string }
      const { kind: _k, ...rest } = row
      R[s] = { ...rest, spec: s, streaming: false }
      saveCompare({ message, order, results: { ...R } })
      return
    }
    if (ev.kind === 'grade' && s && R[s]) {
      R[s] = { ...R[s], quality: ev.quality ?? null }
      saveCompare({ message, order, results: { ...R } })
    }
  }

  const runCompare = async () => {
    const models = [...effectivePicked]
    if (!message.trim() || !models.length || running) return

    clearEditing()
    setRunning(true)
    setCompareRunning(true)
    setOrder(models)
    setResults({})
    setRaceError(null)
    setGrading(null)

    const R: Record<string, CompareResult> = {}
    setResults({ ...R })

    try {
      for await (const ev of api.compareStream({
        message,
        models,
        judge,
        judge_model: judge ? judgeModel : undefined,
      })) {
        if (ev.kind === 'grading') {
          setGrading({ n: ev.n, judge: ev.judge, done: 0 })
        } else if (ev.kind === 'grade') {
          handleStreamEvent(ev, R)
          setResults({ ...R })
          setGrading((g) =>
            g ? { ...g, done: (g.done ?? 0) + 1 } : g,
          )
        } else if (ev.kind === 'done') {
          setGrading(null)
          if (ev.error) setRaceError(String(ev.error))
        } else {
          handleStreamEvent(ev, R)
          setResults({ ...R })
        }
      }
    } catch (e) {
      setRaceError(e instanceof Error ? e.message : String(e))
    }

    setRunning(false)
    setCompareRunning(false)
    saveCompare({ message, order: models, results: R })
    await loadHistory()
    if (onRefresh) await onRefresh()
  }

  const clearCards = () => {
    if (running) return
    setOrder(null)
    setResults(null)
    setRaceError(null)
    saveCompare({ message, order: null, results: null })
    clearEditing()
  }

  const regradeRun = async () => {
    if (regrading) return
    setRegrading(true)
    clearEditing()
    try {
      const r = await api.compareRegrade({
        judge_model: judgeModel,
        only_missing: false,
      })
      const next = applyHistory(r)
      setHistory(next.history)
      setAggregate(next.aggregate)
      const last = next.history[0]
      if (last && results) {
        const updated = { ...results }
        for (const x of last.results ?? []) {
          const spec = x.spec || toSpec(x.model || '')
          if (updated[spec]) {
            updated[spec] = { ...updated[spec], quality: x.quality }
          }
        }
        setResults(updated)
        saveCompare({ message, order, results: updated })
      }
    } catch (e) {
      setRaceError(
        `re-grade failed: ${e instanceof Error ? e.message : String(e)}`,
      )
    }
    setRegrading(false)
    clearEditing()
  }

  const gradeCard = async (spec: string) => {
    if (!results?.[spec] || results[spec]._grading) return
    const next = {
      ...results,
      [spec]: { ...results[spec], _grading: true },
    }
    setResults(next)
    clearEditing()
    try {
      const r = await api.compareRegrade({ spec, judge_model: judgeModel })
      const hist = applyHistory(r)
      setHistory(hist.history)
      setAggregate(hist.aggregate)
      const row = hist.history[0]?.results?.find((x) => x.spec === spec)
      if (row) {
        setResults((prev) =>
          prev
            ? {
                ...prev,
                [spec]: {
                  ...prev[spec],
                  quality: row.quality,
                  _grading: false,
                },
              }
            : prev,
        )
      }
    } catch (e) {
      setRaceError(
        `grade failed: ${e instanceof Error ? e.message : String(e)}`,
      )
      setResults((prev) =>
        prev
          ? {
              ...prev,
              [spec]: { ...prev[spec], _grading: false },
            }
          : prev,
      )
    }
    clearEditing()
  }

  const clearAllHistory = async () => {
    if (
      !confirm(
        'Clear the compare scoreboard and race history? (Only the arena log — your real data is untouched.)',
      )
    ) {
      return
    }
    const r = await api.compareClear()
    setHistory(r.runs ?? [])
    setAggregate(r.aggregate ?? [])
    clearEditing()
  }

  const deleteRun = async (ts: string) => {
    if (!confirm('Delete just this run from the scoreboard? (Other races stay.)')) {
      return
    }
    try {
      const r = await api.compareDeleteRun({ ts })
      const next = applyHistory(r)
      setHistory(next.history)
      setAggregate(next.aggregate)
    } catch (e) {
      setRaceError(
        `delete failed: ${e instanceof Error ? e.message : String(e)}`,
      )
    }
    clearEditing()
  }

  const openRun = (idx: number) => {
    const run = history[idx]
    if (!run) return
    const ids = (run.results ?? []).map(
      (r) => r.model || modelFromSpec(r.spec || ''),
    )
    const mapped: Record<string, CompareResult> = {}
    for (const r of run.results ?? []) {
      const adapted = adaptHistResult(r)
      const spec = adapted.spec || toSpec(adapted.model || '')
      mapped[spec] = adapted
    }
    setOrder(ids)
    setResults(mapped)
    setMessage(run.message || message)
    clearEditing()
  }

  const judgeOptions = judgeModelOptions(
    data?.settings?.small_model,
    pinnedIds,
  )
  const n = effectivePicked.size
  const showGrid = order && order.length > 0
  const resultMap = results ?? {}

  return (
    <>
      <PageHead title={t.compare} home={data?.home} agoSec={agoSec} />

      <div className="card">
        <div className="mb-1.5 flex flex-wrap items-center gap-3">
          <span className="meta">
            One message, every model at once — same harness, isolated homes, real
            receipts (gate, latency, cost, tools). Compare, do not guess.
          </span>
          <label
            className={cn('cmp-judge ms-auto', judge && 'on')}
            title="Grade each reply 0-10 for how well it serves the request"
          >
            <input
              type="checkbox"
              checked={judge}
              onChange={() => {
                setJudge((v) => !v)
                clearEditing()
              }}
            />
            grade — referee
            <select
              value={judgeModel}
              disabled={!judge}
              onChange={(e) => {
                setJudgeModel(e.target.value)
                clearEditing()
              }}
              onClick={(e) => e.stopPropagation()}
              dir="ltr"
            >
              {judgeOptions.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </label>
          <Button
            type="button"
            className="cmp-race"
            disabled={!n || running}
            onClick={() => void runCompare()}
            dir="ltr"
          >
            {running ? 'Racing…' : `Race ${n} model${n === 1 ? '' : 's'}`}
          </Button>
        </div>

        <Textarea
          className="cmp-input min-h-0"
          rows={2}
          value={message}
          onFocus={markEditing}
          onChange={(e) => {
            markEditing()
            setMessage(e.target.value)
          }}
          dir="auto"
        />

        <div className="cmp-picks">
          {pickIds.length ? (
            pickIds.map((id) => {
              const on = effectivePicked.has(id)
              const isPinned = pinnedIds.includes(id)
              return (
                <label key={id} className={cn('cmp-pick', on && 'on')}>
                  <input
                    type="checkbox"
                    checked={on}
                    onChange={() => toggleModel(id)}
                  />
                  <span dir="ltr">
                    {id}
                    {isPinned ? ' · pin' : ''}
                  </span>
                </label>
              )
            })
          ) : (
            <div className="meta">{t.noPins}</div>
          )}
        </div>
      </div>

      {showGrid ? (
        <ResultCols
          order={order}
          results={resultMap}
          sortBy={sortBy}
          running={running}
          grading={grading}
          raceError={raceError}
          regrading={regrading}
          onSort={(k) => {
            setSortBy(k)
            clearEditing()
          }}
          onRegradeRun={() => void regradeRun()}
          onClearCards={clearCards}
          onGradeCard={(spec) => void gradeCard(spec)}
        />
      ) : null}

      <Scoreboard
        aggregate={aggregate}
        history={history}
        order={order ?? []}
        results={resultMap}
        running={running}
        boardSort={boardSort}
        onBoardSort={setBoardSortKey}
        onClearAll={() => void clearAllHistory()}
        onDeleteRun={(ts) => void deleteRun(ts)}
        onOpenRun={openRun}
      />
    </>
  )
}
