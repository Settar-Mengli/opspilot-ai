import { useEffect, useId, type MouseEvent, type RefObject } from 'react'

export interface UseOverlayOptions {
  open: boolean
  onClose: () => void
  closeOnEscape?: boolean
  lockScroll?: boolean
  /** Dialog root for focus trap; when omitted, trap/return-focus are skipped. */
  containerRef?: RefObject<HTMLElement | null>
}

type EscapeEntry = { id: string; onClose: () => void }

const escapeStack: EscapeEntry[] = []
let scrollLockCount = 0
let previousBodyOverflow = ''

function focusableSelector(): string {
  return [
    'a[href]',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(',')
}

function getFocusable(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(focusableSelector())).filter(
    (el) => !el.hasAttribute('disabled') && el.tabIndex !== -1 && el.offsetParent !== null,
  )
}

export function useOverlay({
  open,
  onClose,
  closeOnEscape = true,
  lockScroll = true,
  containerRef,
}: UseOverlayOptions): {
  onBackdropClick: (e: MouseEvent<HTMLElement>) => void
} {
  const id = useId()

  // Escape: only the topmost registered overlay closes.
  useEffect(() => {
    if (!open || !closeOnEscape) return
    const entry: EscapeEntry = { id, onClose }
    escapeStack.push(entry)
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      const top = escapeStack[escapeStack.length - 1]
      if (top?.id !== id) return
      e.stopPropagation()
      onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      const idx = escapeStack.findIndex((e) => e.id === id)
      if (idx >= 0) escapeStack.splice(idx, 1)
    }
  }, [open, closeOnEscape, onClose, id])

  // Scroll lock via refcount so stacked overlays do not unlock early.
  useEffect(() => {
    if (!open || !lockScroll) return
    if (scrollLockCount === 0) {
      previousBodyOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
    }
    scrollLockCount += 1
    return () => {
      scrollLockCount = Math.max(0, scrollLockCount - 1)
      if (scrollLockCount === 0) {
        document.body.style.overflow = previousBodyOverflow
      }
    }
  }, [open, lockScroll])

  // Focus trap + return-focus when a container ref is provided.
  useEffect(() => {
    if (!open || !containerRef) return
    const container = containerRef.current
    if (!container) return

    const previouslyFocused =
      document.activeElement instanceof HTMLElement ? document.activeElement : null

    const focusInitial = () => {
      const nodes = getFocusable(container)
      ;(nodes[0] ?? container).focus()
    }
    // Defer so portal/layout paint completes (matches AskPanel autofocus delay).
    const t = window.setTimeout(focusInitial, 0)

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return
      const nodes = getFocusable(container)
      if (nodes.length === 0) {
        e.preventDefault()
        container.focus()
        return
      }
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      const active = document.activeElement
      if (e.shiftKey) {
        if (active === first || !container.contains(active)) {
          e.preventDefault()
          last.focus()
        }
      } else if (active === last || !container.contains(active)) {
        e.preventDefault()
        first.focus()
      }
    }
    container.addEventListener('keydown', onKeyDown)

    return () => {
      window.clearTimeout(t)
      container.removeEventListener('keydown', onKeyDown)
      if (previouslyFocused && document.contains(previouslyFocused)) {
        previouslyFocused.focus()
      }
    }
  }, [open, containerRef])

  return {
    onBackdropClick: (e) => {
      if (e.target === e.currentTarget) onClose()
    },
  }
}
