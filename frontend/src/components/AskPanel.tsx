import { useId, useRef } from 'react'
import type { AskDraftCard, AskMessage, AskToolStep } from '../api/types'
import { useOverlay } from '../hooks/useOverlay'
import { AskThreadBody } from './AskDock'

interface Props {
  open: boolean
  assistantName: string
  messages: AskMessage[]
  toolSteps?: AskToolStep[]
  draft?: AskDraftCard | null
  onDraftSubjectChange?: (value: string) => void
  onDraftBodyChange?: (value: string) => void
  onApproveDraft?: () => void
  input: string
  loading: boolean
  error: string | null
  onInputChange: (value: string) => void
  onSubmit: () => void
  onClose: () => void
}

export function AskPanel({
  open,
  assistantName,
  messages,
  toolSteps,
  draft,
  onDraftSubjectChange,
  onDraftBodyChange,
  onApproveDraft,
  input,
  loading,
  error,
  onInputChange,
  onSubmit,
  onClose,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const titleId = useId()

  const { onBackdropClick } = useOverlay({ open, onClose, containerRef: panelRef })

  if (!open) return null

  return (
    <div className="ask-panel-overlay" onClick={onBackdropClick}>
      <div
        ref={panelRef}
        className="ask-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ask-panel-header">
          <div className="ask-panel-title" id={titleId}>
            <span className="ask-panel-orb">{assistantName.charAt(0).toUpperCase()}</span>
            <span>Ask {assistantName}</span>
          </div>
          <button type="button" className="ask-panel-close" onClick={onClose} aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <AskThreadBody
          assistantName={assistantName}
          messages={messages}
          toolSteps={toolSteps}
          draft={draft}
          onDraftSubjectChange={onDraftSubjectChange}
          onDraftBodyChange={onDraftBodyChange}
          onApproveDraft={onApproveDraft}
          input={input}
          loading={loading}
          error={error}
          onInputChange={onInputChange}
          onSubmit={onSubmit}
          inputRef={inputRef}
          focusToken={open ? 1 : 0}
          variant="modal"
        />
      </div>
    </div>
  )
}
