import type {
  ApiSettings,
  CalendarMeeting,
  Capability,
  InsightsResponse,
  RunMetadata,
  RunPipelineResult,
  RunSummary,
  SyncResult,
  TriageRecord,
} from './types'

const FALLBACK_API_BASE_URL = 'http://127.0.0.1:8000'
export const API_PREFIX = '/api/v1'

const LOCAL_HOSTNAMES = new Set(['localhost', '127.0.0.1'])

function sanitizeBaseUrl(url: string | undefined): string {
  if (!url) {
    return FALLBACK_API_BASE_URL
  }

  try {
    const parsed = new URL(url)
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return FALLBACK_API_BASE_URL
    }

    if (!LOCAL_HOSTNAMES.has(parsed.hostname)) {
      return FALLBACK_API_BASE_URL
    }

    return parsed.origin
  } catch {
    return FALLBACK_API_BASE_URL
  }
}

const API_BASE_URL = sanitizeBaseUrl(import.meta.env.VITE_API_BASE_URL)

function toApiError(status: number, detail: unknown): Error {
  let code: string | undefined
  if (detail && typeof detail === 'object') {
    const record = detail as Record<string, unknown>
    if (record.error && typeof record.error === 'object') {
      const nested = record.error as Record<string, unknown>
      if (typeof nested.code === 'string') {
        code = nested.code
      }
    }
  }

  const envelopeMessage = messageFromErrorEnvelope(detail)
  let message: string
  if (envelopeMessage) {
    message = `${status}: ${envelopeMessage}`
  } else if (typeof detail === 'string') {
    message = `${status}: ${detail}`
  } else if (detail && typeof detail === 'object') {
    const record = detail as Record<string, unknown>
    message = typeof record.message === 'string' ? `${status}: ${record.message}` : `${status}: Request failed`
  } else {
    message = `${status}: Request failed`
  }

  const err = new Error(message) as Error & { code?: string; status?: number }
  err.code = code
  err.status = status
  return err
}

/** Parse `{ error: { code, message, details? } }` from API error payloads. */
export function messageFromErrorEnvelope(detail: unknown): string | null {
  if (!detail || typeof detail !== 'object') {
    return null
  }
  const record = detail as Record<string, unknown>
  if (!record.error || typeof record.error !== 'object') {
    return null
  }
  const nested = record.error as Record<string, unknown>
  if (typeof nested.message !== 'string') {
    return null
  }
  return nested.message
}

export function isErrorEnvelope(detail: unknown): detail is {
  error: { code: string; message: string; details?: unknown }
} {
  if (!detail || typeof detail !== 'object') {
    return false
  }
  const record = detail as Record<string, unknown>
  if (!record.error || typeof record.error !== 'object') {
    return false
  }
  const nested = record.error as Record<string, unknown>
  return typeof nested.code === 'string' && typeof nested.message === 'string'
}

async function getErrorDetail(response: Response): Promise<unknown> {
  try {
    const payload = await response.json()
    if (payload && typeof payload === 'object' && 'error' in payload) {
      return payload
    }
    if (payload && typeof payload === 'object' && 'detail' in payload) {
      return (payload as { detail: unknown }).detail
    }
    return payload
  } catch {
    return response.text()
  }
}

async function requestText(path: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${path}`, { credentials: 'include' })
  if (!response.ok) {
    const detail = await getErrorDetail(response)
    throw toApiError(response.status, detail)
  }

  return response.text()
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
  })
  if (!response.ok) {
    const detail = await getErrorDetail(response)
    throw toApiError(response.status, detail)
  }

  return response.json() as Promise<T>
}

function isRecord(value: unknown): value is TriageRecord {
  if (!value || typeof value !== 'object') {
    return false
  }

  const candidate = value as Record<string, unknown>
  return (
    typeof candidate.id === 'string' &&
    typeof candidate.urgency === 'string' &&
    typeof candidate.urgency_reason === 'string' &&
    typeof candidate.category === 'string' &&
    typeof candidate.category_reason === 'string' &&
    typeof candidate.sentiment === 'string' &&
    typeof candidate.sentiment_reason === 'string'
  )
}

function isRunSummary(value: unknown): value is RunSummary {
  if (!value || typeof value !== 'object') {
    return false
  }

  const candidate = value as Record<string, unknown>
  return typeof candidate.run_id === 'string'
}

function toRunSummary(value: unknown): RunSummary {
  if (!isRunSummary(value)) {
    throw new Error('Unexpected run metadata payload')
  }

  return value
}

export async function getHealth(): Promise<boolean> {
  const text = await requestText('/api/v1/health')
  return text.trim().toLowerCase() === 'ok'
}

export async function getBriefing(): Promise<string> {
  return requestText('/api/v1/briefing')
}

export async function getTriage(): Promise<TriageRecord[]> {
  const payload = await requestJson<unknown>('/api/v1/triage')
  if (!Array.isArray(payload)) {
    throw new Error('Unexpected triage response shape')
  }

  const records = payload.filter(isRecord)
  if (records.length !== payload.length) {
    console.warn(
      `Dropped ${payload.length - records.length} invalid triage record(s) from response`,
    )
  }

  return records
}

export async function getRuns(): Promise<RunSummary[]> {
  const payload = await requestJson<unknown>('/api/v1/runs')
  if (!Array.isArray(payload)) {
    throw new Error('Unexpected runs response shape')
  }

  return payload.map(toRunSummary)
}

export async function getRunMetadata(runId: string): Promise<RunMetadata> {
  const encodedRunId = encodeURIComponent(runId)
  const payload = await requestJson<unknown>(`/api/v1/runs/${encodedRunId}`)
  return toRunSummary(payload)
}

export async function getRunTriage(runId: string): Promise<TriageRecord[]> {
  const encodedRunId = encodeURIComponent(runId)
  const payload = await requestJson<unknown>(`/api/v1/runs/${encodedRunId}/triage`)
  if (!Array.isArray(payload)) {
    throw new Error('Unexpected run triage response shape')
  }

  const records = payload.filter(isRecord)
  if (records.length !== payload.length) {
    console.warn(
      `Dropped ${payload.length - records.length} invalid run triage record(s) from response`,
    )
  }

  return records
}

export async function getRunBriefing(runId: string): Promise<string> {
  const encodedRunId = encodeURIComponent(runId)
  return requestText(`/api/v1/runs/${encodedRunId}/briefing`)
}

export async function runPipeline(inputFile: string, date: string): Promise<RunPipelineResult> {
  return requestJson<RunPipelineResult>('/api/v1/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input_file: inputFile, date }),
  })
}

export async function getAiBriefing(): Promise<string> {
  return requestText('/api/v1/ai-briefing')
}

export async function getRunAiBriefing(runId: string): Promise<string> {
  const encodedRunId = encodeURIComponent(runId)
  return requestText(`/api/v1/runs/${encodedRunId}/ai-briefing`)
}

export async function getInputFiles(): Promise<string[]> {
  const payload = await requestJson<{ files: string[] }>('/api/v1/inputs')
  return payload.files
}

export async function getApiSettings(): Promise<ApiSettings> {
  return requestJson<ApiSettings>('/api/v1/settings')
}

export { API_BASE_URL }

export async function askOpsPilot(question: string, assistantName: string): Promise<string> {
  const data = await requestJson<{ answer?: string }>('/api/v1/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, assistant_name: assistantName }),
  })
  return data.answer || ''
}

export async function getEveningSummary(assistantName: string): Promise<string> {
  const data = await requestJson<{ summary?: string }>('/api/v1/evening-summary', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assistant_name: assistantName }),
  })
  return data.summary || ''
}

export async function getInsights(assistantName: string): Promise<InsightsResponse> {
  const data = await requestJson<Record<string, unknown>>('/api/v1/insights', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assistant_name: assistantName }),
  })
  return {
    intro: typeof data.intro === 'string' ? data.intro : '',
    insights: Array.isArray(data.insights) ? (data.insights as InsightsResponse['insights']) : [],
  }
}

export async function getCapabilities(): Promise<Capability[]> {
  const payload = await requestJson<unknown>('/api/v1/capabilities')
  if (!Array.isArray(payload)) {
    throw new Error('Unexpected capabilities response shape')
  }
  return payload as Capability[]
}

export async function postSync(): Promise<SyncResult> {
  return requestJson<SyncResult>('/api/v1/sync', { method: 'POST' })
}

export async function disconnectGoogle(): Promise<void> {
  await requestJson<{ status: string }>('/api/v1/oauth/google', { method: 'DELETE' })
}

export async function getCalendarWeek(start: string, end: string): Promise<CalendarMeeting[]> {
  const q = new URLSearchParams({ start, end })
  const payload = await requestJson<{ meetings?: CalendarMeeting[] }>(`/api/v1/calendar/week?${q}`)
  return Array.isArray(payload.meetings) ? payload.meetings : []
}

export async function editMailDraft(
  draftId: string,
  subject: string,
  body: string,
): Promise<{ id: string; subject: string; body: string; to_addrs: string; payload_sha256: string }> {
  return requestJson(`/api/v1/mail/drafts/${encodeURIComponent(draftId)}/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, body }),
  })
}

export async function approveMailDraft(
  draftId: string,
  payloadSha256: string,
  idempotencyKey?: string,
): Promise<{ status: string }> {
  return requestJson(`/api/v1/mail/drafts/${encodeURIComponent(draftId)}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      payload_sha256: payloadSha256,
      idempotency_key: idempotencyKey,
    }),
  })
}
