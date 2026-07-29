import { request, requestStream, type RequestOptions } from '@/lib/http'
import type {
  CompareHistoryResponse,
  CompareStreamEvent,
  DashboardData,
  MemoryActionBody,
  MemoryActionResponse,
  ModelCatalog,
  PinAction,
  PinResponse,
  QueryResponse,
  RevealResponse,
  SessionActionResponse,
  SettingsApplyResponse,
  StreamEvent,
} from '@/lib/types'

export const api = {
  get: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'GET' }),

  post: <T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>,
  ) => request<T>(path, { ...options, method: 'POST', body }),

  put: <T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>,
  ) => request<T>(path, { ...options, method: 'PUT', body }),

  patch: <T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>,
  ) => request<T>(path, { ...options, method: 'PATCH', body }),

  delete: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'DELETE' }),

  /** Full dashboard snapshot — poll ~every 5s. */
  data: () => api.get<DashboardData>('/api/data'),

  events: (cursor: number | null) =>
    api.get<{
      events: Array<{ type?: string; decision?: string; [key: string]: unknown }>
      cursor: number
    }>(cursor == null ? '/api/events' : `/api/events?cursor=${cursor}`),

  settings: (body: Record<string, unknown>) =>
    api.post<SettingsApplyResponse>('/api/settings', body),

  pin: (body: { action: PinAction; id: string }) =>
    api.post<PinResponse>('/api/pin', body),

  models: () => api.get<ModelCatalog>('/api/models'),

  memory: (body: MemoryActionBody) =>
    api.post<MemoryActionResponse>('/api/memory', body),

  query: (body: { sql: string }) => api.post<QueryResponse>('/api/query', body),

  reveal: (path: string) =>
    api.get<RevealResponse>(`/api/reveal?path=${encodeURIComponent(path)}`),

  compareHistory: () => api.get<CompareHistoryResponse>('/api/compare/history'),

  compareClear: () => api.post<CompareHistoryResponse & { ok?: boolean }>('/api/compare/clear'),

  compareRegrade: (body: Record<string, unknown> = {}) =>
    api.post<CompareHistoryResponse>('/api/compare/regrade', body),

  compareDeleteRun: (body: { ts: string }) =>
    api.post<CompareHistoryResponse>('/api/compare/delete_run', body),

  session: (body: {
    action: 'new' | 'switch' | 'history'
    session_id?: string
  }) => api.post<SessionActionResponse>('/api/session', body),

  /** SSE stream — yields parsed `data:` JSON events until the body ends. */
  async *chatStream(
    message: string,
    options: { sessionId?: string; signal?: AbortSignal } = {},
  ): AsyncGenerator<StreamEvent> {
    const response = await requestStream(
      '/api/chat/stream',
      { message, session_id: options.sessionId },
      { signal: options.signal },
    )
    if (!response.body) {
      return
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const part of parts) {
        for (const line of part.split('\n')) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data:')) continue
          const raw = trimmed.slice(5).trim()
          if (!raw) continue
          try {
            yield JSON.parse(raw) as StreamEvent
          } catch {
            // skip malformed SSE chunks
          }
        }
      }
    }
  },

  /** SSE compare race — yields parsed `data:` JSON events until the body ends. */
  async *compareStream(
    body: Record<string, unknown>,
    options: { signal?: AbortSignal } = {},
  ): AsyncGenerator<CompareStreamEvent> {
    const response = await requestStream('/api/compare/stream', body, {
      signal: options.signal,
    })
    if (!response.body) {
      return
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const part of parts) {
        for (const line of part.split('\n')) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data:')) continue
          const raw = trimmed.slice(5).trim()
          if (!raw) continue
          try {
            yield JSON.parse(raw) as CompareStreamEvent
          } catch {
            // skip malformed SSE chunks
          }
        }
      }
    }
  },
}
