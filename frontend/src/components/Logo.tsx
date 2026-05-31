export function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
      <circle cx="18" cy="18" r="16" fill="url(#logo-grad)" />
      <text
        x="18"
        y="22"
        textAnchor="middle"
        fontFamily="Inter, sans-serif"
        fontSize="12"
        fontWeight="700"
        fill="white"
      >
        OP
      </text>
    </svg>
  )
}
