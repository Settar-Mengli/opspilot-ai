import { useEffect, type MouseEvent } from 'react'

export interface UseOverlayOptions {
  open: boolean
  onClose: () => void
  closeOnEscape?: boolean
  lockScroll?: boolean
}

export function useOverlay({
  open,
  onClose,
  closeOnEscape = true,
  lockScroll = true,
}: UseOverlayOptions): {
  onBackdropClick: (e: MouseEvent<HTMLElement>) => void
} {
  useEffect(() => {
    if (!open || !closeOnEscape) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, closeOnEscape, onClose])

  useEffect(() => {
    if (!open || !lockScroll) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [open, lockScroll])

  return {
    onBackdropClick: (e) => {
      if (e.target === e.currentTarget) onClose()
    },
  }
}
