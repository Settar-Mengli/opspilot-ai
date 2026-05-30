import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { getHealth } from './api/client'
import { ApiUnavailableBanner } from './components/ApiUnavailableBanner'
import { HealthIndicator } from './components/HealthIndicator'
import { DashboardPage } from './pages/DashboardPage'
import { ExecutiveBriefingPage } from './pages/ExecutiveBriefingPage'
import { TriageExplorerPage } from './pages/TriageExplorerPage'

function App() {
  const [apiHealthy, setApiHealthy] = useState(false)
  const [healthLoading, setHealthLoading] = useState(true)
  const [refreshToken, setRefreshToken] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function checkHealth() {
      setHealthLoading(true)
      try {
        const health = await getHealth()
        if (!cancelled) {
          setApiHealthy(health)
        }
      } catch {
        if (!cancelled) {
          setApiHealthy(false)
        }
      } finally {
        if (!cancelled) {
          setHealthLoading(false)
        }
      }
    }

    void checkHealth()

    return () => {
      cancelled = true
    }
  }, [refreshToken])

  function handleRetry() {
    setRefreshToken((value) => value + 1)
  }

  return (
    <div className="app-shell">
      <header className="top-nav">
        <div className="brand-block">
          <h1>OpsPilot Command Center</h1>
          <p>Local-only operational intelligence console</p>
        </div>

        <nav className="route-nav" aria-label="Primary">
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/triage">Triage Explorer</NavLink>
          <NavLink to="/briefing">Executive Briefing</NavLink>
        </nav>

        <HealthIndicator isHealthy={apiHealthy} isLoading={healthLoading} />
      </header>

      <ApiUnavailableBanner visible={!healthLoading && !apiHealthy} onRetry={handleRetry} />

      <main className="content-shell">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage refreshToken={refreshToken} />} />
          <Route path="/triage" element={<TriageExplorerPage refreshToken={refreshToken} />} />
          <Route path="/briefing" element={<ExecutiveBriefingPage refreshToken={refreshToken} />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
