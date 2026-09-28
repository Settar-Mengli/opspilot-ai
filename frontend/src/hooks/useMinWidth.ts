import { useEffect, useState } from 'react'

/** Justified for Ask dual-mode keyboard/open behavior (L5/L6). JS mount is authoritative for rail/Ask (≥1280); CSS hide is a safety default only. */
export function useMinWidth(px: number): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(`(min-width: ${px}px)`).matches : false,
  )

  useEffect(() => {
    const mq = window.matchMedia(`(min-width: ${px}px)`)
    const onChange = () => setMatches(mq.matches)
    onChange()
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [px])

  return matches
}
