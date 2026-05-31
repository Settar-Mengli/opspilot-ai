import { useState } from 'react'

const STORAGE_KEY = 'opspilot.assistantName'
const DEFAULT_NAME = 'Pilot'

function readStoredName(): string {
  if (typeof window === 'undefined') return DEFAULT_NAME
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored && stored.trim()) {
    return stored.trim()
  }
  return DEFAULT_NAME
}

export function useAssistantName(): [string, (name: string) => void, boolean] {
  const [name, setNameState] = useState<string>(() => readStoredName())
  const [hasChosen, setHasChosen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return !!window.localStorage.getItem(STORAGE_KEY)
  })

  const setName = (next: string) => {
    const clean = next.trim().slice(0, 20)
    if (clean) {
      window.localStorage.setItem(STORAGE_KEY, clean)
      setNameState(clean)
      setHasChosen(true)
    }
  }

  return [name, setName, hasChosen]
}
