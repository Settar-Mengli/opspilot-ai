import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { getApiSettings, patchApiSettings } from '../api/client'
import type { AIProvider, ApiSettings, PatchApiSettingsRequest } from '../api/types'

function toKnownProvider(provider: string): AIProvider {
  return provider === 'openai' ? 'openai' : 'anthropic'
}

export function SettingsPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<ApiSettings | null>(null)
  const [provider, setProvider] = useState<AIProvider>('anthropic')
  const [model, setModel] = useState('claude-haiku-4-5-20251001')
  const [apiKey, setApiKey] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  const refreshSettings = useCallback(async (showLoader: boolean) => {
    if (showLoader) {
      setLoading(true)
    }

    try {
      const latest = await getApiSettings()
      setStatus(latest)
      setProvider(toKnownProvider(latest.provider))
      setModel(latest.model)
      setApiKey('')
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load settings.')
    } finally {
      if (showLoader) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    void refreshSettings(true)
  }, [refreshSettings])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setSaveMessage('')
    setErrorMessage('')

    const payload: PatchApiSettingsRequest = {
      provider,
      model: model.trim(),
    }

    if (apiKey.trim()) {
      payload.api_key = apiKey.trim()
    }

    try {
      await patchApiSettings(payload)
      await refreshSettings(false)
      setSaveMessage('Saved.')
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Unable to save settings.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-page">
      <div className="page-header">
        <button className="page-back" onClick={() => navigate('/dashboard')} aria-label="Back to dashboard">
          <ArrowLeft size={20} strokeWidth={2} />
        </button>
        <h2 className="page-header-title">Settings</h2>
      </div>

      <div className="settings-card">
        <p className="settings-section-title">AI Provider</p>

        <form className="settings-form" onSubmit={handleSubmit}>
          <label className="settings-label" htmlFor="provider-select">Provider</label>
          <select
            id="provider-select"
            className="settings-input"
            value={provider}
            onChange={(event) => setProvider(event.target.value as AIProvider)}
          >
            <option value="anthropic">anthropic</option>
            <option value="openai">openai</option>
          </select>

          <label className="settings-label" htmlFor="model-input">Model</label>
          <input
            id="model-input"
            className="settings-input"
            type="text"
            value={model}
            onChange={(event) => setModel(event.target.value)}
            autoComplete="off"
          />

          <label className="settings-label" htmlFor="api-key-input">API key</label>
          <input
            id="api-key-input"
            className="settings-input"
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="sk-••••"
            autoComplete="off"
          />
          <p className="settings-help">For security, saved keys are never shown in full and are not pre-filled.</p>

          <button className="settings-save" type="submit" disabled={saving || loading}>
            {saving ? 'Saving…' : 'Save'}
          </button>

          {saveMessage && <p className="settings-success">{saveMessage}</p>}
          {errorMessage && <p className="settings-error">{errorMessage}</p>}
        </form>
      </div>

      <div className="settings-card settings-card--status">
        <p className="settings-section-title">Current Status</p>

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
              <span className="settings-status-label">API key preview</span>
              <span className="settings-status-value">{status?.api_key_preview ?? 'not set'}</span>
            </p>
          </>
        )}
      </div>
    </div>
  )
}
