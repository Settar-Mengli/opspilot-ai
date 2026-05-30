import type { TriageRecord } from './types'

const FALLBACK_API_BASE_URL = 'http://127.0.0.1:8000'

function sanitizeBaseUrl(url: string | undefined): string {
  if (!url) {
    return FALLBACK_API_BASE_URL
  }

  try {
    const parsed = new URL(url)
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
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

async function requestText(path: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    let detail: unknown = null
    try {
      detail = await response.json()
      if (detail && typeof detail === 'object' && 'detail' in detail) {
        detail = (detail as { detail: unknown }).detail
      }
    } catch {
      detail = await response.text()
    }
    throw toApiError(response.status, detail)
  }

  return response.text()
}

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    let detail: unknown = null
    try {
      detail = await response.json()
      if (detail && typeof detail === 'object' && 'detail' in detail) {
        detail = (detail as { detail: unknown }).detail
      }
    } catch {
      detail = await response.text()
    }
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

export { API_BASE_URL }
