/** Sole reader of `import.meta.env` — components never touch Vite env directly. */

const DEFAULT_API_BASE = 'http://127.0.0.1:7777'

function readApiBase(): string {
  // Optional: unset → loopback default; "" → same-origin Vite proxy in dev.
  const raw = import.meta.env.VITE_API_BASE_URL
  if (raw === undefined || raw === null) {
    return DEFAULT_API_BASE
  }
  if (typeof raw !== 'string') {
    throw new Error('VITE_API_BASE_URL must be a string when set')
  }
  return raw.replace(/\/$/, '')
}

export const env = {
  apiBaseUrl: readApiBase(),
} as const
