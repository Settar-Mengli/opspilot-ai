import { useId } from 'react'

interface BulBulAvatarProps {
  size?: number
}

export function BulBulAvatar({ size = 56 }: BulBulAvatarProps) {
  const uid = useId()
  const gradientId = `bbAvatar-${uid}`

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="bulbul-avatar"
    >
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#9CAB7A" />
          <stop offset="100%" stopColor="#647349" />
        </linearGradient>
      </defs>
      <circle cx="28" cy="28" r="28" fill={`url(#${gradientId})`} />
      <circle cx="28" cy="26" r="11" fill="#FAF9F5" opacity="0.96" />
      <ellipse cx="28" cy="44" rx="16" ry="11" fill="#FAF9F5" opacity="0.96" />
      <circle cx="25" cy="25" r="1.6" fill="#141413" />
      <circle cx="31" cy="25" r="1.6" fill="#141413" />
      <path
        d="M 24 30 Q 28 32.5 32 30"
        stroke="#141413"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  )
}
