import { renderMarkdown } from '@/lib/markdown'
import { cn } from '@/lib/utils'

type Props = {
  html: string
  className?: string
  dir?: 'auto' | 'ltr' | 'rtl'
}

/** Renders escape-first markdown HTML. */
export function Markdown({ html, className, dir = 'auto' }: Props) {
  return (
    <div
      className={cn('md-body text-[var(--ink2)]', className)}
      dir={dir}
      // Safe: renderMarkdown escapes first, then applies a fixed transform set.
      dangerouslySetInnerHTML={{ __html: html || renderMarkdown('') }}
    />
  )
}

export function MarkdownText({
  text,
  className,
  dir = 'auto',
}: {
  text: string
  className?: string
  dir?: 'auto' | 'ltr' | 'rtl'
}) {
  return <Markdown html={renderMarkdown(text)} className={className} dir={dir} />
}
