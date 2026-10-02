import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_PREFIX, approveMailDraft, editMailDraft, formatMailHitlError } from './client'

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses the /api/v1 prefix', () => {
    expect(API_PREFIX).toBe('/api/v1')
  })

  it('editMailDraft posts subject and body only', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: 'md_1',
        subject: 'Re: Hi',
        body: 'Thanks',
        to_addrs: 'demo@example.com',
        payload_sha256: 'a'.repeat(64),
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const result = await editMailDraft('md_1', 'Re: Hi', 'Thanks')
    expect(result.id).toBe('md_1')
    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/mail/drafts/md_1/edit')
    expect(JSON.parse(String(init.body))).toEqual({ subject: 'Re: Hi', body: 'Thanks' })
  })

  it('approveMailDraft posts payload hash', async () => {
    const hash = 'b'.repeat(64)
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'sent' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const result = await approveMailDraft('md_1', hash, 'idem-1')
    expect(result.status).toBe('sent')
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/mail/drafts/md_1/approve')
    expect(JSON.parse(String(init.body))).toEqual({
      payload_sha256: hash,
      idempotency_key: 'idem-1',
    })
  })

  it('formatMailHitlError maps status codes with request id', () => {
    const mk = (status: number, code: string, requestId = 'req-1') =>
      Object.assign(new Error('x'), { status, code, requestId })
    expect(formatMailHitlError(mk(409, 'draft_already_claimed'))).toContain('already sent')
    expect(formatMailHitlError(mk(409, 'draft_already_claimed'))).toContain('ref req-1')
    expect(formatMailHitlError(mk(403, 'demo_mode_blocks_send'))).toContain('Demo mode')
    expect(formatMailHitlError(mk(403, 'recipient_not_allowlisted'))).toContain('allowlist')
    expect(formatMailHitlError(mk(403, 'draft_owner_mismatch'))).toContain('do not own')
    expect(formatMailHitlError(mk(429, 'send_daily_cap'))).toContain('Daily send limit')
    expect(formatMailHitlError(mk(422, 'unsafe_subject'))).toContain('rejected')
    expect(formatMailHitlError(mk(502, 'send_outcome_unknown'))).toBe(
      'Send may have gone through. Check the Sent folder before trying again. (ref req-1)',
    )
    expect(formatMailHitlError(mk(500, 'internal_error'))).toContain('server error')
  })

  it('formatMailHitlError_send_outcome_unknown_copy', () => {
    const err = Object.assign(new Error('x'), { status: 502, code: 'send_outcome_unknown' })
    expect(formatMailHitlError(err)).toBe(
      'Send may have gone through. Check the Sent folder before trying again.',
    )
  })

  it('formatMailHitlError_gmail_unavailable_not_sent_copy', () => {
    const err = Object.assign(new Error('x'), { status: 503, code: 'gmail_unavailable_not_sent' })
    expect(formatMailHitlError(err)).toBe('Gmail was unavailable. Nothing was sent — try again.')
  })
})
