import { useState } from 'react'

const STORAGE_KEY = 'opspilot.userName'

function readStoredName(): string | null {
  if (typeof window === 'undefined') return null
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored && stored.trim()) {
    return stored.trim()
  }
  return null
}

export function useUserName(): [string | null, (name: string) => void] {
  const [name, setNameState] = useState<string | null>(() => readStoredName())

  const setName = (next: string) => {
    const clean = next.trim().slice(0, 40)
    if (clean) {
      try {
        window.localStorage.setItem(STORAGE_KEY, clean)
      } catch {
        // localStorage may be unavailable (private browsing, full quota).
        // The in-memory state still works for the current session.
      }
      setNameState(clean)
    }
  }

  return [name, setName]
}
