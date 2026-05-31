import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useSearchParams } from 'react-router-dom'
import { getHealth, getRuns } from './api/client'
import type { RunSummary } from './api/types'
import { ApiUnavailableBanner } from './components/ApiUnavailableBanner'
import { HealthIndicator } from './components/HealthIndicator'
import { Logo } from './components/Logo'
import { RunSelector } from './components/RunSelector'
import { DashboardPage } from './pages/DashboardPage'
import { ExecutiveBriefingPage } from './pages/ExecutiveBriefingPage'
import { TriageExplorerPage } from './pages/TriageExplorerPage'

function App() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [apiHealthy, setApiHealthy] = useState(false)
  const [healthLoading, setHealthLoading] = useState(true)
  const [refreshToken, setRefreshToken] = useState(0)
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [runsLoading, setRunsLoading] = useState(true)
  const [runsError, setRunsError] = useState<string | null>(null)

  const selectedRunId = searchParams.get('run_id')?.trim() || null

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

  useEffect(() => {
    let cancelled = false

    async function loadRuns() {
      setRunsLoading(true)
      setRunsError(null)
      try {
        const payload = await getRuns()
        if (!cancelled) {
          setRuns(payload)
        }
      } catch (loadError) {
        if (!cancelled) {
          setRunsError(loadError instanceof Error ? loadError.message : 'Failed to load run history')
        }
      } finally {
        if (!cancelled) {
          setRunsLoading(false)
        }
      }
    }

    void loadRuns()

    return () => {
      cancelled = true
    }
  }, [refreshToken])

  function handleRetry() {
    setRefreshToken((value) => value + 1)
  }

  function handleSelectRun(runId: string | null) {
    const nextParams = new URLSearchParams(searchParams)
    if (runId) {
      nextParams.set('run_id', runId)
    } else {
      nextParams.delete('run_id')
    }
    setSearchParams(nextParams)
  }

  return (
    <div className="app-shell">
      <header className="top-nav">
        <div className="brand-block">
          <Logo size={28} />
          <h1>OpsPilot</h1>
        </div>
        <nav className="route-nav" aria-label="Primary">
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/triage">Triage Explorer</NavLink>
          <NavLink to="/briefing">Executive Briefing</NavLink>
        </nav>
        <div className="run-controls">
          <RunSelector
            runs={runs}
            selectedRunId={selectedRunId}
            isLoading={runsLoading}
            error={runsError}
            onSelectRun={handleSelectRun}
          />
          <HealthIndicator isHealthy={apiHealthy} isLoading={healthLoading} />
        </div>
      </header>

      <ApiUnavailableBanner visible={!healthLoading && !apiHealthy} onRetry={handleRetry} />

      <main className="content-shell">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/dashboard"
            element={
              <DashboardPage
                refreshToken={refreshToken}
                selectedRunId={selectedRunId}
                runs={runs}
                runsLoading={runsLoading}
                runsError={runsError}
                onSelectRun={handleSelectRun}
                onRefresh={handleRetry}
              />
            }
          />
          <Route
            path="/triage"
            element={
              <TriageExplorerPage
                refreshToken={refreshToken}
                selectedRunId={selectedRunId}
                onSelectLatest={() => handleSelectRun(null)}
              />
            }
          />
          <Route
            path="/briefing"
            element={
              <ExecutiveBriefingPage
                refreshToken={refreshToken}
                selectedRunId={selectedRunId}
                onSelectLatest={() => handleSelectRun(null)}
              />
            }
          />
        </Routes>
      </main>
    </div>
  )
}

export default App
