import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { getApiSettings } from '../api/client'
import type { ApiSettings } from '../api/types'

export function SettingsPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<ApiSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    let cancelled = false

    getApiSettings()
      .then((latest) => {
        if (cancelled) {
          return
        }
        setStatus(latest)
      })
      .catch((error) => {
        if (cancelled) {
          return
        }
        setErrorMessage(error instanceof Error ? error.message : 'Failed to load settings.')
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="settings-page">
      <div className="page-header">
        <button
          className="page-back"
          onClick={() => navigate('/dashboard')}
          aria-label="Back to dashboard"
        >
          <ArrowLeft size={20} strokeWidth={2} />
        </button>
        <h2 className="page-header-title">Settings</h2>
      </div>

      <div className="settings-card settings-card--status">
        <p className="settings-section-title">AI settings (read-only)</p>
        <p className="settings-help">
          Provider and keys are configured via environment variables only. Runtime PATCH is disabled.
        </p>

        {loading && !status ? (
          <p className="settings-status-row">Loading current settings…</p>
        ) : (
          <>
            <p className="settings-status-row">
              <span className="settings-status-label">Active provider</span>
              <span className="settings-status-value">{status?.provider ?? 'unknown'}</span>
            </p>
            <p className="settings-status-row">
              <span className="settings-status-label">Active model</span>
              <span className="settings-status-value">{status?.model ?? 'unknown'}</span>
            </p>
            <p className="settings-status-row">
              <span className="settings-status-label">API key set</span>
              <span className="settings-status-value">{status?.api_key_set ? 'yes' : 'no'}</span>
            </p>
          </>
        )}
        {errorMessage && <p className="settings-error">{errorMessage}</p>}
      </div>
    </div>
  )
}
