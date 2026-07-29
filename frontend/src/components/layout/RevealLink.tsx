import type { ReactNode } from 'react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

type Props = {
  path: string
  children: ReactNode
  className?: string
}

export function RevealLink({ path, children, className }: Props) {
  return (
    <button
      type="button"
      className={cn(
        'cursor-pointer border-0 bg-transparent p-0 text-[var(--accent)] underline',
        className,
      )}
      dir="ltr"
      onClick={() => {
        void api.reveal(path)
      }}
    >
      {children}
    </button>
  )
}
