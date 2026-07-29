import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

type EditingContextValue = {
  editing: boolean
  markEditing: () => void
  clearEditing: () => void
  setEditing: (value: boolean) => void
}

const EditingContext = createContext<EditingContextValue | null>(null)

export function EditingProvider({ children }: { children: ReactNode }) {
  const [editing, setEditingState] = useState(false)

  const markEditing = useCallback(() => {
    setEditingState(true)
  }, [])

  const clearEditing = useCallback(() => {
    setEditingState(false)
  }, [])

  const setEditing = useCallback((value: boolean) => {
    setEditingState(value)
  }, [])

  const value = useMemo(
    () => ({ editing, markEditing, clearEditing, setEditing }),
    [editing, markEditing, clearEditing, setEditing],
  )

  return <EditingContext.Provider value={value}>{children}</EditingContext.Provider>
}

export function useEditing(): EditingContextValue {
  const ctx = useContext(EditingContext)
  if (!ctx) throw new Error('useEditing must be used within EditingProvider')
  return ctx
}
