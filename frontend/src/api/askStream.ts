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
    throw new Error(`${response.status}: Ask stream failed`)
  }
  if (!response.body) {
    throw new Error('Ask stream missing body')
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
        handlers.onError?.(String(ev.message || 'Ask failed.'))
      }
    }
  }
}

/** Exported for vitest. */
export const _parseSseChunkForTest = parseSseChunk
