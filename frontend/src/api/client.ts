import type { RunMetadata, RunPipelineResult, RunSummary, TriageRecord, InsightsResponse } from './types'

const FALLBACK_API_BASE_URL = 'http://127.0.0.1:8000'

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
  if (typeof detail === 'string') {
    return new Error(`${status}: ${detail}`)
  }

  if (detail && typeof detail === 'object' && 'message' in detail) {
    return new Error(`${status}: ${String((detail as { message: unknown }).message)}`)
  }

  return new Error(`${status}: Request failed`)
}

async function getErrorDetail(response: Response): Promise<unknown> {
  try {
    const payload = await response.json()
    if (payload && typeof payload === 'object' && 'detail' in payload) {
      return (payload as { detail: unknown }).detail
    }
    return payload
  } catch {
    return response.text()
  }
}

async function requestText(path: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    const detail = await getErrorDetail(response)
    throw toApiError(response.status, detail)
  }

  return response.text()
}

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
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
  const text = await requestText('/health')
  return text.trim().toLowerCase() === 'ok'
}

export async function getBriefing(): Promise<string> {
  return requestText('/briefing')
}

export async function getTriage(): Promise<TriageRecord[]> {
  const payload = await requestJson<unknown>('/triage')
  if (!Array.isArray(payload)) {
    throw new Error('Unexpected triage response shape')
  }

  const records = payload.filter(isRecord)
  if (records.length !== payload.length) {
    throw new Error('Unexpected triage record payload')
  }

  return records
}

export async function getRuns(): Promise<RunSummary[]> {
  const payload = await requestJson<unknown>('/runs')
  if (!Array.isArray(payload)) {
    throw new Error('Unexpected runs response shape')
  }

  return payload.map(toRunSummary)
}

export async function getRunMetadata(runId: string): Promise<RunMetadata> {
  const encodedRunId = encodeURIComponent(runId)
  const payload = await requestJson<unknown>(`/runs/${encodedRunId}`)
  return toRunSummary(payload)
}

export async function getRunTriage(runId: string): Promise<TriageRecord[]> {
  const encodedRunId = encodeURIComponent(runId)
  const payload = await requestJson<unknown>(`/runs/${encodedRunId}/triage`)
  if (!Array.isArray(payload)) {
    throw new Error('Unexpected run triage response shape')
  }

  const records = payload.filter(isRecord)
  if (records.length !== payload.length) {
    throw new Error('Unexpected run triage record payload')
  }

  return records
}

export async function getRunBriefing(runId: string): Promise<string> {
  const encodedRunId = encodeURIComponent(runId)
  return requestText(`/runs/${encodedRunId}/briefing`)
}

export async function runPipeline(inputFile: string, date: string): Promise<RunPipelineResult> {
  const response = await fetch(`${API_BASE_URL}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input_file: inputFile, date }),
  })
  if (!response.ok) {
    const detail = await getErrorDetail(response)
    throw toApiError(response.status, detail)
  }
  return response.json() as Promise<RunPipelineResult>
}

export async function getAiBriefing(): Promise<string> {
  return requestText('/ai-briefing')
}

export async function getRunAiBriefing(runId: string): Promise<string> {
  const encodedRunId = encodeURIComponent(runId)
  return requestText(`/runs/${encodedRunId}/ai-briefing`)
}

export async function getInputFiles(): Promise<string[]> {
  const payload = await requestJson<{ files: string[] }>('/inputs')
  return payload.files
}

export { API_BASE_URL }

export async function askOpsPilot(question: string, assistantName: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, assistant_name: assistantName }),
  })
  if (!response.ok) {
    throw new Error(`Ask failed: ${response.status} ${response.statusText}`)
  }
  const data = await response.json()
  return data.answer || ''
}

export async function getEveningSummary(assistantName: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/evening-summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assistant_name: assistantName }),
  })
  if (!response.ok) {
    throw new Error(`Evening summary failed: ${response.status} ${response.statusText}`)
  }
  const data = await response.json()
  return data.summary || ''
}

export async function getInsights(assistantName: string): Promise<InsightsResponse> {
  const response = await fetch(`${API_BASE_URL}/insights`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assistant_name: assistantName }),
  })
  if (!response.ok) {
    throw new Error(`Insights failed: ${response.status} ${response.statusText}`)
  }
  const data = await response.json()
  return {
    intro: typeof data.intro === 'string' ? data.intro : '',
    insights: Array.isArray(data.insights) ? data.insights : [],
  }
}
