/** Logical collapse / reopen chevrons that flip with `dir`. */

export function CollapseStart({ className }: { className?: string }) {
  return (
    <span className={className} aria-hidden>
      <span className="inline rtl:hidden">{'‹'}</span>
      <span className="hidden rtl:inline">{'›'}</span>
    </span>
  )
}

export function CollapseEnd({ className }: { className?: string }) {
  return (
    <span className={className} aria-hidden>
      <span className="inline rtl:hidden">{'›'}</span>
      <span className="hidden rtl:inline">{'‹'}</span>
    </span>
  )
}
