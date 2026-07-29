import { request, requestStream, type RequestOptions } from '@/lib/http'
import type {
  DashboardData,
  SessionActionResponse,
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
}
