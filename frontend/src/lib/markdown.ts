/**
 * Escape-first tiny markdown — port of waku `ops/static/js/util.js`.
 * Escape `&<>` first, then bold/italic/code/links (http + message only)/lists/tables.
 * No sanitizer library.
 */

const ESC: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
}

export function esc(s: unknown): string {
  return (s ?? '').toString().replace(/[&<>]/g, (c) => ESC[c] ?? c)
}

/** `s` is already HTML-escaped. */
function mdInline(s: string): string {
  return s
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+|message:\/\/[^\s)]+)\)/g,
      (_m, text: string, url: string) =>
        `<a href="${url}" target="_blank" rel="noopener">${text}</a>`,
    )
    .replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>')
    .replace(
      /(^|[^*_`])[*_]([^*_`\s][^*_`]*?)[*_](?![\w*])/g,
      '$1<em>$2</em>',
    )
    .replace(/`([^`]+?)`/g, '<code>$1</code>')
}

export function renderMarkdown(text: string): string {
  const lines = esc(text).split(/\r?\n/)
  const row = (l: string) => /^\s*\|.*\|\s*$/.test(l)
  const sep = (l: string) => /^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/.test(l)
  const cells = (l: string) =>
    l
      .trim()
      .replace(/^\||\|$/g, '')
      .split('|')
      .map((c) => c.trim())
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    const l = lines[i] ?? ''
    if (row(l) && i + 1 < lines.length && sep(lines[i + 1] ?? '')) {
      const head = cells(l)
      i += 2
      const body: string[][] = []
      while (i < lines.length && row(lines[i] ?? '')) {
        body.push(cells(lines[i] ?? ''))
        i++
      }
      out.push(
        `<table class="mdtable"><thead><tr>${head
          .map((h) => `<th>${mdInline(h)}</th>`)
          .join('')}</tr></thead><tbody>${body
          .map(
            (r) =>
              `<tr>${r.map((c) => `<td>${mdInline(c)}</td>`).join('')}</tr>`,
          )
          .join('')}</tbody></table>`,
      )
      continue
    }
    const h = l.match(/^\s*#{1,6}\s+(.*)$/)
    if (h) {
      out.push(`<div class="mdh">${mdInline(h[1] ?? '')}</div>`)
      i++
      continue
    }
    if (/^\s*[-*]\s+/.test(l)) {
      const items: string[] = []
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i] ?? '')) {
        items.push(mdInline((lines[i] ?? '').replace(/^\s*[-*]\s+/, '')))
        i++
      }
      out.push(
        `<ul class="mdlist">${items.map((x) => `<li>${x}</li>`).join('')}</ul>`,
      )
      continue
    }
    if (/^\s*\d+\.\s+/.test(l)) {
      const items: string[] = []
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i] ?? '')) {
        items.push(mdInline((lines[i] ?? '').replace(/^\s*\d+\.\s+/, '')))
        i++
      }
      out.push(
        `<ol class="mdlist">${items.map((x) => `<li>${x}</li>`).join('')}</ol>`,
      )
      continue
    }
    if (/^\s*$/.test(l)) {
      i++
      continue
    }
    const para: string[] = []
    while (
      i < lines.length &&
      (lines[i] ?? '').trim() &&
      !/^\s*[-*]\s|^\s*\d+\.\s|^\s*#{1,6}\s/.test(lines[i] ?? '') &&
      !(row(lines[i] ?? '') && i + 1 < lines.length && sep(lines[i + 1] ?? ''))
    ) {
      para.push(mdInline(lines[i] ?? ''))
      i++
    }
    out.push(`<div class="mdp">${para.join('<br>')}</div>`)
  }
  return out.join('')
}
