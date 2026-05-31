import { useState } from 'react'

interface Props {
  onSubmit: (name: string) => void
}

export function Onboarding({ onSubmit }: Props) {
  const [name, setName] = useState('')

  function submit() {
    const clean = name.trim()
    if (clean) onSubmit(clean)
  }

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-card">
        <div className="onboarding-orb">P</div>

        <div className="onboarding-title">Hello, I'm Pilot.</div>

        <div className="onboarding-text">
          I'll be your chief of staff — keeping your operations
          tidy so you can focus on what matters. What should I
          call you?
        </div>

        <input
          className="onboarding-input"
          placeholder="Your first name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
          maxLength={40}
          autoFocus
        />
        <button
          className="onboarding-submit"
          disabled={!name.trim()}
          onClick={submit}
        >
          Let's begin →
        </button>
      </div>
    </div>
  )
}
