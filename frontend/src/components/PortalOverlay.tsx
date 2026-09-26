import { createPortal } from 'react-dom'
import { useOverlay } from '../hooks/useOverlay'

interface PortalOverlayProps {
  open: boolean
  onClose: () => void
  children: React.ReactNode
  className?: string
  closeOnEscape?: boolean
  lockScroll?: boolean
  role?: string
  ariaLabel?: string
}

/** Thin portal + shared open/close lifecycle. Panels keep their own CSS classes. */
export function PortalOverlay({
  open,
  onClose,
  children,
  className,
  closeOnEscape = true,
  lockScroll = true,
  role = 'dialog',
  ariaLabel,
}: PortalOverlayProps) {
  const { onBackdropClick } = useOverlay({ open, onClose, closeOnEscape, lockScroll })

  if (!open) return null

  return createPortal(
    <div
      className={className}
      onClick={onBackdropClick}
      role={role}
      aria-modal="true"
      aria-label={ariaLabel}
    >
      {children}
    </div>,
    document.body,
  )
}
