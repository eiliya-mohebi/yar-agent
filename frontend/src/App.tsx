import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Shell } from '@/components/layout/Shell'
import { LangProvider } from '@/hooks/useLang'

function ShellRoutes() {
  const location = useLocation()
  if (location.pathname === '/') {
    return <Navigate to="/overview" replace />
  }
  return <Shell />
}

export function App() {
  return (
    <LangProvider>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/*" element={<ShellRoutes />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </LangProvider>
  )
}
