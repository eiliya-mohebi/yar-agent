/** Display helpers ported from waku `render.js`. */

export function money(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '$0.00'
  return '$' + (n < 0.01 ? n.toFixed(4) : n.toFixed(2))
}

export function secs(ms: number | null | undefined): string {
  if (ms == null) return '—'
  return (ms / 1000).toFixed(1) + 's'
}

export function stripToolsAnnotation(text: string): string {
  return (text || '').replace(/\s*\[tools used:[\s\S]*\]\s*$/, '').trim()
}
