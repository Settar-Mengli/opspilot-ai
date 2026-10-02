import { API_BASE_URL } from './client'

/** Feature gate: Approve/send API is wired (D-033 / C6). */
export const ASK_APPROVE_ENABLED = true

export interface AskStreamHandlers {
  onToken?: (text: string) => void
  onToolStart?: (tool: string, args: unknown) => void
  onToolEnd?: (tool: string, ok: boolean) => void
  onDraft?: (draft: {
    draft_id: string
    subject: string
    body: string
    to_addrs: string
  }) => void
  onFinal?: (answer: string) => void
  onError?: (message: string) => void
}

/** Sync-style Ask error copy: code + optional ref request_id. */
export function formatAskStreamError(ev: {
  code?: unknown
  request_id?: unknown
  message?: unknown
}): string {
  const code = typeof ev.code === 'string' && ev.code.trim() ? ev.code.trim() : 'ask_failed'
  const rid = typeof ev.request_id === 'string' && ev.request_id.trim() ? ev.request_id.trim() : undefined
  const parts = [code, rid ? `ref ${rid}` : null].filter(Boolean)
  return `Ask failed (${parts.join('; ')})`
}

function parseSseChunk(buffer: string): { events: Record<string, unknown>[]; rest: string } {
  const events: Record<string, unknown>[] = []
  const parts = buffer.split('\n\n')
  const rest = parts.pop() ?? ''
  for (const part of parts) {
    for (const line of part.split('\n')) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (!raw) continue
      try {
        events.push(JSON.parse(raw) as Record<string, unknown>)
      } catch {
        // ignore malformed
      }
    }
  }
  return { events, rest }
}

async function httpAskFailureMessage(response: Response): Promise<string> {
  const headerRid = response.headers.get('X-Request-ID') || undefined
  let code = 'ask_stream_http'
  let requestId = headerRid
  try {
    const body = (await response.json()) as {
      error?: { code?: string; request_id?: string }
      detail?: { error?: { code?: string; request_id?: string } }
    }
    const nested = body.error ?? body.detail?.error
    if (nested?.code) code = nested.code
    if (nested?.request_id) requestId = nested.request_id
  } catch {
    // non-JSON body — keep header rid / default code
  }
  return formatAskStreamError({ code, request_id: requestId })
}

export async function askOpsPilotStream(
  question: string,
  assistantName: string,
  history: { role: string; content: string }[],
  handlers: AskStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/ask/stream`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      assistant_name: assistantName,
      history: history.slice(-10),
    }),
    signal,
  })
  if (!response.ok) {
    throw new Error(await httpAskFailureMessage(response))
  }
  if (!response.body) {
    throw new Error(formatAskStreamError({ code: 'ask_stream_empty', request_id: response.headers.get('X-Request-ID') }))
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parsed = parseSseChunk(buffer)
    buffer = parsed.rest
    for (const ev of parsed.events) {
      const type = String(ev.type || '')
      if (type === 'token' && typeof ev.text === 'string') {
        handlers.onToken?.(ev.text)
      } else if (type === 'tool_start') {
        handlers.onToolStart?.(String(ev.tool || ''), ev.args)
      } else if (type === 'tool_end') {
        handlers.onToolEnd?.(String(ev.tool || ''), Boolean(ev.ok))
      } else if (type === 'draft' && typeof ev.draft_id === 'string') {
        handlers.onDraft?.({
          draft_id: ev.draft_id,
          subject: String(ev.subject || ''),
          body: String(ev.body || ''),
          to_addrs: String(ev.to_addrs || ''),
        })
      } else if (type === 'final') {
        handlers.onFinal?.(String(ev.answer || ''))
      } else if (type === 'error') {
        handlers.onError?.(formatAskStreamError(ev))
      }
    }
  }
}

/** Exported for vitest. */
export const _parseSseChunkForTest = parseSseChunk
