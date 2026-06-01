import { useId } from 'react'

interface BulBulAvatarProps {
  size?: number
  assistantName?: string
}

export function BulBulAvatar({ size = 56, assistantName }: BulBulAvatarProps) {
  const uid = useId()
  const glowGradientId = `bbGlow-${uid}`

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label={assistantName ? `${assistantName} presence` : 'Assistant presence'}
      className="bulbul-avatar"
    >
      <defs>
        <radialGradient id={glowGradientId}>
          <stop offset="0%" stopColor="#9CAB7A" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#9CAB7A" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="28" cy="28" r="24" className="bulbul-avatar__halo" />
      <circle cx="28" cy="28" r="18" fill={`url(#${glowGradientId})`} />
      <circle cx="28" cy="28" r="11" fill="#9CAB7A" />
    </svg>
  )
}
