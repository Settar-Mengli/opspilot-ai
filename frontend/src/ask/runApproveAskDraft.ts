/** Shared Approve → edit → send flow used by App (and Vitest). */

import { formatMailHitlError } from '../api/client'
import type { AskDraftCard } from '../api/types'

export type EditMailDraftFn = (
  id: string,
  subject: string,
  body: string,
) => Promise<{ id: string; payload_sha256: string }>

export type ApproveMailDraftFn = (
  id: string,
  hash: string,
  key?: string,
) => Promise<{ status: string; send_failed?: boolean; error_code?: string | null }>

export type DraftUpdater = (fn: (d: AskDraftCard | null) => AskDraftCard | null) => void

const REOPENABLE_CODES = new Set([
  'no_google_credential',
  'google_reauth_required',
  'gmail_send_failed',
  'send_failed',
])

/**
 * Approve path: read draft via getDraft() before any setState side effects,
 * then edit + approve. Always clears approving in finally.
 */
export async function runApproveAskDraft(options: {
  getDraft: () => AskDraftCard | null
  setDraft: DraftUpdater
  editMailDraft: EditMailDraftFn
  approveMailDraft: ApproveMailDraftFn
}): Promise<void> {
  const current = options.getDraft()
  if (!current || current.sentAt || current.approving) return

  const holdKey = current.idempotencyKey || crypto.randomUUID()
  const holdDraft = {
    draftId: current.draftId,
    subject: current.subject,
    body: current.body,
  }

  options.setDraft((d) =>
    d && d.draftId === holdDraft.draftId && !d.sentAt && !d.approving
      ? {
          ...d,
          approveError: null,
          approving: true,
          idempotencyKey: holdKey,
        }
      : d,
  )

  try {
    const edited = await options.editMailDraft(holdDraft.draftId, holdDraft.subject, holdDraft.body)
    const result = await options.approveMailDraft(edited.id, edited.payload_sha256, holdKey)
    const code = result.error_code ?? undefined
    const failed = result.status === 'failed' || result.send_failed === true
    if (failed) {
      const unknown = code === 'send_outcome_unknown'
      const reopenable = code !== undefined && REOPENABLE_CODES.has(code)
      options.setDraft((d) =>
        d
          ? {
              ...d,
              draftId: edited.id,
              approveError: code ? `Send failed (${code})` : 'Send failed.',
              idempotencyKey: crypto.randomUUID(),
              sendOutcomeUnknown: unknown,
              reopenable,
            }
          : d,
      )
      return
    }
    options.setDraft((d) =>
      d
        ? {
            ...d,
            sentAt: Date.now(),
            approveError: null,
            sendOutcomeUnknown: false,
            reopenable: false,
          }
        : d,
    )
  } catch (e) {
    const message = formatMailHitlError(e)
    const code =
      typeof e === 'object' && e && 'code' in e && typeof (e as { code?: string }).code === 'string'
        ? (e as { code: string }).code
        : undefined
    const unknown = code === 'send_outcome_unknown'
    const reopenable = code !== undefined && REOPENABLE_CODES.has(code)
    options.setDraft((d) =>
      d
        ? {
            ...d,
            approveError: message,
            idempotencyKey: crypto.randomUUID(),
            sendOutcomeUnknown: unknown,
            reopenable,
          }
        : d,
    )
  } finally {
    options.setDraft((d) => (d ? { ...d, approving: false } : d))
  }
}
