import { env } from '@/lib/env'

const DEFAULT_TIMEOUT_MS = 30_000

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export type RequestOptions = {
  method?: HttpMethod
  body?: unknown
  headers?: Record<string, string>
  timeoutMs?: number
  signal?: AbortSignal
}

export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown
  readonly isNetworkError: boolean

  constructor(
    message: string,
    options: {
      status: number
      detail?: unknown
      isNetworkError?: boolean
    },
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status
    this.detail = options.detail
    this.isNetworkError = options.isNetworkError ?? false
  }
}

function buildUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  const base = env.apiBaseUrl
  if (!base) {
    return path.startsWith('/') ? path : `/${path}`
  }
  return path.startsWith('/') ? `${base}${path}` : `${base}/${path}`
}

async function parseErrorBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    try {
      return await response.json()
    } catch {
      return null
    }
  }
  try {
    const text = await response.text()
    return text.length > 0 ? text : null
  } catch {
    return null
  }
}

function errorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim() !== '') {
    return detail
  }
  if (
    detail !== null &&
    typeof detail === 'object' &&
    'detail' in detail &&
    typeof (detail as { detail: unknown }).detail === 'string'
  ) {
    return (detail as { detail: string }).detail
  }
  if (
    detail !== null &&
    typeof detail === 'object' &&
    'error' in detail &&
    typeof (detail as { error: unknown }).error === 'string'
  ) {
    return (detail as { error: string }).error
  }
  return fallback
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    method = 'GET',
    body,
    headers = {},
    timeoutMs = DEFAULT_TIMEOUT_MS,
    signal: outerSignal,
  } = options

  const requestHeaders = new Headers(headers)
  if (body !== undefined && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
  }

  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  const onOuterAbort = () => controller.abort()
  if (outerSignal) {
    if (outerSignal.aborted) {
      controller.abort()
    } else {
      outerSignal.addEventListener('abort', onOuterAbort, { once: true })
    }
  }

  try {
    const response = await fetch(buildUrl(path), {
      method,
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })

    if (!response.ok) {
      const detail = await parseErrorBody(response)
      throw new ApiError(errorMessage(detail, response.statusText), {
        status: response.status,
        detail,
      })
    }

    if (response.status === 204) {
      return undefined as T
    }

    const contentType = response.headers.get('content-type') ?? ''
    if (!contentType.includes('application/json')) {
      return undefined as T
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('Request timed out', {
        status: 0,
        isNetworkError: true,
      })
    }
    if (error instanceof TypeError) {
      throw new ApiError('Network error', {
        status: 0,
        isNetworkError: true,
      })
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
    if (outerSignal) {
      outerSignal.removeEventListener('abort', onOuterAbort)
    }
  }
}

/** POST that returns a raw Response (for SSE). Caller owns the body stream. */
export async function requestStream(
  path: string,
  body: unknown,
  options: { signal?: AbortSignal } = {},
): Promise<Response> {
  const response = await fetch(buildUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: options.signal,
  })
  if (!response.ok) {
    const detail = await parseErrorBody(response)
    throw new ApiError(errorMessage(detail, response.statusText), {
      status: response.status,
      detail,
    })
  }
  return response
}
