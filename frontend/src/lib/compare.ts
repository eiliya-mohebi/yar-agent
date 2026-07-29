import type { CompareAggregate, CompareResult } from '@/lib/types'

export const COMPARE_STORAGE_KEY = 'yar_compare'

export const DEFAULT_COMPARE_MESSAGE =
  'Build a Kanto team around Pikachu — search current picks, remember it, and schedule two training sessions this week.'

export type SortMetric = 'latency' | 'cost' | 'tokens'

export type BoardSortKey =
  | 'total_cost_usd'
  | 'total_latency_ms'
  | 'total_tokens_in'
  | 'total_tokens_out'
  | 'total_tokens'
  | 'runs'
  | 'cases_passed'
  | 'quality_avg'

export type BoardSort = { key: BoardSortKey; dir: 'asc' | 'desc' }

/** Backend accepts plain ids; events use openai: prefix. */
export function toSpec(modelId: string): string {
  const raw = modelId.trim()
  if (raw.includes(':')) return raw
  return `openai:${raw}`
}

export function modelFromSpec(spec: string): string {
  const idx = spec.indexOf(':')
  return idx >= 0 ? spec.slice(idx + 1) : spec
}

let compareRunning = false

/** Shell / poll guards call this to avoid mid-race overwrite. */
export function isCompareRunning(): boolean {
  return compareRunning
}

export function setCompareRunning(value: boolean): void {
  compareRunning = value
}

export function compareErrorReason(err: string | undefined): string | null {
  const e = (err || '').toLowerCase()
  if (e.includes('429') || e.includes('rate limit')) {
    return 'rate limited — try again shortly'
  }
  if (
    e.includes('401') ||
    e.includes('api key') ||
    e.includes('authentication') ||
    e.includes('invalid_api_key')
  ) {
    return 'missing or invalid API key'
  }
  if (
    e.includes('not found') ||
    e.includes('no longer available') ||
    e.includes('does not exist')
  ) {
    return 'model id not available'
  }
  if (e.includes('not a chat model') || e.includes('v1/completions')) {
    return 'not a chat model — needs chat completions API'
  }
  if (e.includes('max_tokens') || e.includes('max_completion_tokens')) {
    return 'token-parameter mismatch'
  }
  if (e.includes('unsupported')) {
    return 'unsupported on chat.completions'
  }
  return null
}

export function adaptHistResult(r: CompareResult): CompareResult {
  const gate = r.gate
  return {
    ...r,
    spec: r.spec || toSpec(r.model || ''),
    gate:
      gate == null
        ? null
        : typeof gate === 'object'
          ? gate
          : { decision: String(gate) },
    tools: (r.tools || []).map((t) =>
      typeof t === 'string' ? { tool: t } : t,
    ),
  }
}

export function qualityScore(q: CompareResult['quality']): number | null {
  if (q == null) return null
  if (typeof q === 'number') return q
  return q.score ?? null
}

export function metricValue(
  r: CompareResult,
  sortBy: SortMetric,
): number {
  if (sortBy === 'latency') return r.latency_ms ?? 0
  if (sortBy === 'cost') return r.cost_usd ?? 0
  return (r.tokens_in ?? 0) + (r.tokens_out ?? 0)
}

export function foldLiveAggregate(
  aggregate: CompareAggregate[],
  order: string[],
  results: Record<string, CompareResult>,
  running: boolean,
): CompareAggregate[] {
  const map: Record<string, CompareAggregate> = {}
  for (const a of aggregate) {
    const spec = a.spec || toSpec(a.model || '')
    map[spec] = { ...a, spec }
  }
  if (!running) return Object.values(map)

  for (const modelId of order) {
    const spec = toSpec(modelId)
    const r = results[spec]
    if (!r || r.streaming) continue
    const a =
      map[spec] ??
      (map[spec] = {
        spec,
        provider: r.provider,
        model: r.model ?? modelFromSpec(spec),
        runs: 0,
        ok: 0,
        total_latency_ms: 0,
        total_tokens_in: 0,
        total_tokens_out: 0,
        total_tokens: 0,
        total_cost_usd: 0,
        cases_passed: 0,
        cases_scored: 0,
        quality_n: 0,
        quality_avg: null,
      })
    a.runs = (a.runs ?? 0) + 1
    if (!r.error) {
      a.ok = (a.ok ?? 0) + 1
      a.total_latency_ms = (a.total_latency_ms ?? 0) + (r.latency_ms ?? 0)
      a.total_tokens_in = (a.total_tokens_in ?? 0) + (r.tokens_in ?? 0)
      a.total_tokens_out = (a.total_tokens_out ?? 0) + (r.tokens_out ?? 0)
      a.total_tokens = (a.total_tokens_in ?? 0) + (a.total_tokens_out ?? 0)
      a.total_cost_usd =
        Math.round(((a.total_cost_usd ?? 0) + (r.cost_usd ?? 0)) * 10000) / 10000
    }
    if (r.completion) {
      a.cases_scored = (a.cases_scored ?? 0) + 1
      a.cases_passed = (a.cases_passed ?? 0) + (r.completion.passed ? 1 : 0)
    }
    const qs = qualityScore(r.quality)
    if (qs != null) {
      const prevN = a.quality_n ?? 0
      const prevAvg = a.quality_avg ?? 0
      const nextN = prevN + 1
      a.quality_n = nextN
      a.quality_avg = Math.round(((prevAvg * prevN + qs) / nextN) * 10) / 10
    }
  }
  return Object.values(map)
}

export function judgeModelOptions(
  smallModel: string | undefined,
  pinnedIds: string[],
): string[] {
  const ids = new Set<string>()
  if (smallModel) ids.add(smallModel)
  ids.add('gpt-4.1-mini')
  ids.add('gpt-5.3-chat-latest')
  for (const id of pinnedIds) ids.add(id)
  return [...ids]
}
