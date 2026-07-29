/** Types for `GET /api/data` and related core routes — mirror `collect()`. */

export type GateDecision = {
  decision?: string
  reason?: string
  [key: string]: unknown
}

export type ToolCallRow = {
  tool: string
  args?: unknown
  output?: string
  status?: string
  summary?: string
  [key: string]: unknown
}

export type Turn = {
  user_message?: string
  ts?: string
  gate?: GateDecision | null
  llm_calls?: unknown[]
  tools?: ToolCallRow[]
  reply?: string | null
  iterations?: number
  latency_ms?: number | null
  cost?: number
  consolidation?: { new_facts?: number } | null
  unfinished?: boolean
  [key: string]: unknown
}

export type ChatMeta = {
  gate?: GateDecision | null
  iterations?: number
  latency_ms?: number
  tools?: string[] | ToolCallRow[]
  model?: string
  [key: string]: unknown
}

export type ChatLogRow = {
  role: string
  content: string
  consolidated?: number
  source?: string
  session_id?: string
  meta?: string | ChatMeta | null
  created_at?: string
}

export type SessionRow = {
  id: string
  title?: string
  messages?: number
  last?: string
  last_at?: string
  sources?: string[]
}

export type FactRow = {
  id: number
  subject?: string
  content: string
  source?: string
  created_at?: string
}

export type EpisodeRow = {
  id: number
  happened_at?: string
  summary: string
}

export type SkillRow = {
  name: string
  description: string
  body: string
  path: string
  rel?: string
  editable?: boolean
}

export type CalendarEvent = {
  title: string
  start: string
  end?: string
  attendees?: string
  created_at?: string
}

export type OutboxDraft = {
  name: string
  text: string
}

export type DbTableInfo = {
  name: string
  columns: string[]
  types: Record<string, string>
  count: number
  sample: Record<string, unknown>[]
}

export type DbInfo = {
  path: string
  size: number
  tables: DbTableInfo[]
  fts: string[]
  all_tables: string[]
}

export type SettingsInfo = {
  model: string
  small_model: string
  base_url: string
  api_key_set: boolean
  api_key_last4: string
  pinned: { id: string; default: boolean }[]
  search_key_env?: string
  search_key_set?: boolean
  search_key_last4?: string
}

export type ToolsInfo = {
  catalog?: { name: string; description?: string; source?: string }[]
  mcp?: {
    configured?: boolean
    servers?: string[]
    live?: boolean
  }
  [key: string]: unknown
}

export type UsageSummary = {
  calls: number
  total_in: number
  total_out: number
  total_cost: number
  by_day?: unknown[]
  by_provider?: unknown[]
}

export type Stats = {
  turns: number
  tool_calls: number
  tool_errors: number
  gate_skips: number
  gate_retrieves: number
  tokens_in: number
  tokens_out: number
  cost: number
  latency_avg: number
  latency_p95: number
  trace_files: number
}

export type DashboardData = {
  generated_at: string
  home: string
  provider: string
  model: string
  stats: Stats
  turns: Turn[]
  trace_tail: { type?: string; ts?: string; detail?: string }[]
  trace_file: string | null
  trace_errors: { file: string; error: string }[]
  facts: FactRow[]
  episodes: EpisodeRow[]
  soul: string
  chat_pending: number
  chat_log: ChatLogRow[]
  sessions: SessionRow[]
  current_session: string
  consolidate_every: number
  calendar: CalendarEvent[]
  outbox: OutboxDraft[]
  skills: SkillRow[]
  eval_report: unknown | null
  db: DbInfo
  settings: SettingsInfo
  tools: ToolsInfo
  usage: UsageSummary
}

export type SessionHistoryMessage = {
  role: string
  content: string
  meta?: ChatMeta | null
}

export type SessionActionResponse = {
  ok?: boolean
  session_id?: string
  history?: SessionHistoryMessage[]
  error?: string
}

export type StreamEvent =
  | { kind: 'text'; delta?: string }
  | { kind: 'gate'; decision?: string; reason?: string }
  | {
      kind: 'tool'
      tool?: string
      args?: unknown
      output?: string
    }
  | { kind: 'llm'; [key: string]: unknown }
  | { kind: 'consolidation'; new_facts?: number; [key: string]: unknown }
  | {
      kind: 'done'
      reply?: string
      error?: string
      gate?: GateDecision | null
      tools?: ToolCallRow[]
      consolidation?: { new_facts?: number } | null
      iterations?: number
      latency_ms?: number
      model?: string
      meta?: ChatMeta
      [key: string]: unknown
    }
