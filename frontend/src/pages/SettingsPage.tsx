import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { getApiSettings } from '../api/client'
import type { ApiSettings, JobStatusSummary } from '../api/types'

function formatJobTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function JobBlock({ label, job }: { label: string; job: JobStatusSummary }) {
  const isOk = job.status === 'succeeded' || job.status === 'partial'
  return (
    <div className="settings-card" data-testid={`job-block-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      <p className="settings-section-title">{label}</p>
      <p className="settings-status-row">
        <span className="settings-status-label">Status</span>
        <span className="settings-status-value" style={{ color: isOk ? '#9cab7a' : '#f0a793' }}>
          {job.status}
        </span>
      </p>
      <p className="settings-status-row">
        <span className="settings-status-label">Triaged</span>
        <span className="settings-status-value">{job.triaged}</span>
      </p>
      <p className="settings-status-row">
        <span className="settings-status-label">Pending</span>
        <span className="settings-status-value">{job.pending}</span>
      </p>
      <p className="settings-status-row">
        <span className="settings-status-label">Rules fallback</span>
        <span className="settings-status-value">{job.rules_fallback_count ?? 0}</span>
      </p>
      <p className="settings-status-row">
        <span className="settings-status-label">Re-auth</span>
        <span className="settings-status-value">{job.reauth_needed ? 'needed' : 'ok'}</span>
      </p>
      {job.error_code && (
        <p className="settings-status-row">
          <span className="settings-status-label">Error</span>
          <span className="settings-status-value" style={{ color: '#f0a793' }}>
            {job.error_code}
          </span>
        </p>
      )}
      <p className="settings-status-row">
        <span className="settings-status-label">Finished</span>
        <span className="settings-status-value">{formatJobTime(job.finished_at)}</span>
      </p>
    </div>
  )
}

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
            <p className="settings-status-row">
              <span className="settings-status-label">DEMO_MODE</span>
              <span className="settings-status-value">{status?.demo_mode ? 'on' : 'off'}</span>
            </p>
            <p className="settings-status-row">
              <span className="settings-status-label">Google connected</span>
              <span className="settings-status-value">{status?.google_connected ? 'yes' : 'no'}</span>
            </p>
          </>
        )}
        {errorMessage && <p className="settings-error">{errorMessage}</p>}
      </div>

      {status?.last_morning && <JobBlock label="Last morning run" job={status.last_morning} />}
      {status?.last_sync && <JobBlock label="Last sync" job={status.last_sync} />}
    </div>
  )
}
