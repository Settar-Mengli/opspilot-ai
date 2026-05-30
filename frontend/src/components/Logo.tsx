export function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="hex-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="100%" stopColor="#4f46e5" />
        </linearGradient>
        <filter id="hex-shadow" x="-10%" y="-10%" width="120%" height="120%">
          <feDropShadow dx="0" dy="1" stdDeviation="2" floodColor="#6366f1" floodOpacity="0.4" />
        </filter>
      </defs>
      <polygon
        points="18,2 32,10 32,26 18,34 4,26 4,10"
        fill="url(#hex-grad)"
        filter="url(#hex-shadow)"
      />
      <text
        x="18"
        y="21"
        textAnchor="middle"
        fontFamily="Inter, sans-serif"
        fontSize="11"
        fontWeight="bold"
        fill="white"
      >
        OP
      </text>
    </svg>
  )
}
