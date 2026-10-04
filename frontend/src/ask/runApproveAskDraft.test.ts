import { describe, expect, it, vi } from 'vitest'
import type { AskDraftCard } from '../api/types'
import { runApproveAskDraft } from './runApproveAskDraft'

const baseDraft = (): AskDraftCard => ({
  draftId: 'md_1',
  subject: 'Re: subject',
  body: 'Body',
  toAddrs: 'demo@example.com',
  sentAt: null,
  approveError: null,
  idempotencyKey: 'key-1',
  approving: false,
  sendOutcomeUnknown: false,
})

/** Pre-fix hold-in-setState pattern (b6 before askDraftRef). */
async function runApproveAskDraftLegacyHold(options: {
  setDraft: (fn: (d: AskDraftCard | null) => AskDraftCard | null) => void
  editMailDraft: (id: string, subject: string, body: string) => Promise<{ id: string; payload_sha256: string }>
  approveMailDraft: (
    id: string,
    hash: string,
    key?: string,
  ) => Promise<{ status: string; send_failed?: boolean; error_code?: string | null }>
}): Promise<void> {
  const hold: {
    key: string
    draft: Pick<AskDraftCard, 'draftId' | 'subject' | 'body'> | null
  } = { key: '', draft: null }
  options.setDraft((d) => {
    if (!d || d.sentAt || d.approving) return d
    hold.key = d.idempotencyKey || crypto.randomUUID()
    hold.draft = { draftId: d.draftId, subject: d.subject, body: d.body }
    return {
      ...d,
      approveError: null,
      approving: true,
      idempotencyKey: hold.key,
    }
  })
  if (!hold.draft || !hold.key) return
  try {
    const edited = await options.editMailDraft(hold.draft.draftId, hold.draft.subject, hold.draft.body)
    await options.approveMailDraft(edited.id, edited.payload_sha256, hold.key)
  } finally {
    options.setDraft((d) => (d ? { ...d, approving: false } : d))
  }
}

describe('runApproveAskDraft', () => {
  it('calls editMailDraft on approve; clears approving and sets error + reopenable on throw', async () => {
    let draft: AskDraftCard | null = baseDraft()
    const editMailDraft = vi.fn().mockResolvedValue({
      id: 'md_1',
      payload_sha256: 'a'.repeat(64),
    })
    const approveMailDraft = vi.fn().mockRejectedValue(
      Object.assign(new Error('google_reauth_required'), {
        status: 400,
        code: 'google_reauth_required',
      }),
    )

    await runApproveAskDraft({
      getDraft: () => draft,
      setDraft: (fn) => {
        draft = fn(draft)
      },
      editMailDraft,
      approveMailDraft,
    })

    expect(editMailDraft).toHaveBeenCalledTimes(1)
    expect(editMailDraft).toHaveBeenCalledWith('md_1', 'Re: subject', 'Body')
    expect(approveMailDraft).toHaveBeenCalledTimes(1)
    expect(draft?.approving).toBe(false)
    expect(draft?.reopenable).toBe(true)
    expect(draft?.approveError).toBeTruthy()
  })

  it('calls editMailDraft when setDraft defers updaters (scheduler-sensitive)', async () => {
    let draft: AskDraftCard | null = baseDraft()
    const queue: Array<() => void> = []
    const editMailDraft = vi.fn().mockResolvedValue({
      id: 'md_1',
      payload_sha256: 'a'.repeat(64),
    })
    const approveMailDraft = vi.fn().mockResolvedValue({
      status: 'failed',
      send_failed: false,
      error_code: 'google_reauth_required',
    })

    const pending = runApproveAskDraft({
      getDraft: () => draft,
      setDraft: (fn) => {
        queue.push(() => {
          draft = fn(draft)
        })
      },
      editMailDraft,
      approveMailDraft,
    })

    // Flush deferred setState after approve started (mirrors async scheduler).
    while (queue.length) queue.shift()!()
    await pending
    while (queue.length) queue.shift()!()

    expect(editMailDraft).toHaveBeenCalledTimes(1)
    expect(draft?.approving).toBe(false)
    expect(draft?.reopenable).toBe(true)
  })

  it('pre-fix hold-in-setState skips editMailDraft when setDraft defers updaters', async () => {
    let draft: AskDraftCard | null = baseDraft()
    const queue: Array<() => void> = []
    const editMailDraft = vi.fn().mockResolvedValue({
      id: 'md_1',
      payload_sha256: 'a'.repeat(64),
    })
    const approveMailDraft = vi.fn()

    const pending = runApproveAskDraftLegacyHold({
      setDraft: (fn) => {
        queue.push(() => {
          draft = fn(draft)
        })
      },
      editMailDraft,
      approveMailDraft,
    })

    // Early-return runs before queued updater fills hold — edit never called.
    await pending
    while (queue.length) queue.shift()!()

    expect(editMailDraft).not.toHaveBeenCalled()
    expect(approveMailDraft).not.toHaveBeenCalled()
    // Updater eventually set approving true with no finally (early return).
    expect(draft?.approving).toBe(true)
  })
})
