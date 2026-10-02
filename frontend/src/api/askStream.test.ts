import { describe, expect, it } from 'vitest'
import { _parseSseChunkForTest, ASK_APPROVE_ENABLED, formatAskStreamError } from './askStream'

describe('askStream', () => {
  it('parses SSE data lines', () => {
    const { events, rest } = _parseSseChunkForTest(
      'data: {"type":"token","text":"Hi"}\n\ndata: {"type":"final","answer":"Hi"}\n\npartial',
    )
    expect(events).toHaveLength(2)
    expect(events[0]?.type).toBe('token')
    expect(events[1]?.type).toBe('final')
    expect(rest).toBe('partial')
  })

  it('parses minimized tool_end without draft body', () => {
    const { events } = _parseSseChunkForTest(
      'data: {"type":"tool_end","tool":"draft_reply","ok":true}\n\n' +
        'data: {"type":"draft","draft_id":"md_1","subject":"S","body":"SECRET","to_addrs":"a@b.c"}\n\n',
    )
    expect(events[0]).toEqual({ type: 'tool_end', tool: 'draft_reply', ok: true })
    expect(events[1]?.body).toBe('SECRET')
  })

  it('formats SSE errors with code and ref request_id', () => {
    expect(
      formatAskStreamError({
        code: 'llm_policy_denied',
        request_id: 'req-abc',
        message: 'Ask unavailable: remote LLM disabled by policy.',
      }),
    ).toBe('Ask failed (llm_policy_denied; ref req-abc)')
    expect(formatAskStreamError({ message: 'Ask failed.' })).toBe('Ask failed (ask_failed)')
    expect(formatAskStreamError({ code: 'stream_failed', request_id: 'rid-1' })).toBe(
      'Ask failed (stream_failed; ref rid-1)',
    )
  })

  it('enables Approve after HITL lands', () => {
    expect(ASK_APPROVE_ENABLED).toBe(true)
  })
})
