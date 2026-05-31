import { useState, useEffect } from 'react'

const STORAGE_KEY = 'opspilot.userName'

export function useUserName(): [string | null, (name: string) => void] {
  const [name, setNameState] = useState<string | null>(null)

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && stored.trim()) {
      setNameState(stored.trim())
    }
  }, [])

  const setName = (next: string) => {
    const clean = next.trim().slice(0, 40)
    if (clean) {
      localStorage.setItem(STORAGE_KEY, clean)
      setNameState(clean)
    }
  }

  return [name, setName]
}
