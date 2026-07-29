import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  applyDocumentLang,
  copy,
  loadLang,
  saveLang,
  type Copy,
  type UiLang,
} from '@/lib/i18n'

type LangContextValue = {
  lang: UiLang
  t: Copy
  setLang: (lang: UiLang) => void
  toggleLang: () => void
}

const LangContext = createContext<LangContextValue | null>(null)

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<UiLang>(() => loadLang())

  useEffect(() => {
    applyDocumentLang(lang)
    saveLang(lang)
  }, [lang])

  const setLang = useCallback((next: UiLang) => {
    setLangState(next)
  }, [])

  const toggleLang = useCallback(() => {
    setLangState((prev) => (prev === 'en' ? 'fa' : 'en'))
  }, [])

  const value = useMemo(
    () => ({ lang, t: copy[lang], setLang, toggleLang }),
    [lang, setLang, toggleLang],
  )

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>
}

export function useLang(): LangContextValue {
  const ctx = useContext(LangContext)
  if (!ctx) throw new Error('useLang must be used within LangProvider')
  return ctx
}
