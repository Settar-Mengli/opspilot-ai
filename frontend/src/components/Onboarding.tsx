import { useState } from 'react'

interface Props {
  onComplete: (userName: string, assistantName: string) => void
}

const PRESET_NAMES = ['Ops', 'Aria', 'Ren', 'Nova']

export function Onboarding({ onComplete }: Props) {
  const [step, setStep] = useState<1 | 2>(1)
  const [userName, setUserName] = useState('')
  const [assistantName, setAssistantName] = useState('')
  const [customMode, setCustomMode] = useState(false)

  function goToStep2() {
    const clean = userName.trim()
    if (clean) setStep(2)
  }

  function finish() {
    const cleanUser = userName.trim()
    const cleanAssistant = assistantName.trim()
    if (cleanUser && cleanAssistant) {
      onComplete(cleanUser, cleanAssistant)
    }
  }

  function pickPreset(name: string) {
    setAssistantName(name)
    setCustomMode(false)
  }

  function enterCustomMode() {
    setAssistantName('')
    setCustomMode(true)
  }

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-card">
        <div className="onboarding-orb">
          {step === 1 ? 'O' : (assistantName.charAt(0).toUpperCase() || 'O')}
        </div>

        {step === 1 && (
          <>
            <div className="onboarding-title">Hello, I'm OpsPilot.</div>
            <div className="onboarding-text">
              I'll be your chief of staff — keeping your operations tidy so you can focus on what matters. What should I call you?
            </div>
            <input
              className="onboarding-input"
              autoFocus
              placeholder="Your first name"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') goToStep2() }}
              maxLength={40}
            />
            <button
              className="onboarding-submit"
              disabled={!userName.trim()}
              onClick={goToStep2}
            >
              Continue →
            </button>
            <div className="onboarding-step-indicator">Step 1 of 2</div>
          </>
        )}

        {step === 2 && (
          <>
            <div className="onboarding-title">Nice to meet you, {userName}.</div>
            <div className="onboarding-text">
              What would you like to call me? Pick a name that feels right, or choose your own.
            </div>

            <div className="onboarding-presets">
              {PRESET_NAMES.map(name => (
                <button
                  key={name}
                  className={`onboarding-preset ${assistantName === name && !customMode ? 'selected' : ''}`}
                  onClick={() => pickPreset(name)}
                >
                  {name}
                </button>
              ))}
              <button
                className={`onboarding-preset ${customMode ? 'selected' : ''}`}
                onClick={enterCustomMode}
              >
                + Custom
              </button>
            </div>

            {customMode && (
              <input
                className="onboarding-input"
                autoFocus
                placeholder="Type a name (1-20 characters)"
                value={assistantName}
                onChange={(e) => setAssistantName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') finish() }}
                maxLength={20}
              />
            )}

            <button
              className="onboarding-submit"
              disabled={!assistantName.trim()}
              onClick={finish}
            >
              Let's begin →
            </button>
            <div className="onboarding-step-indicator">
              <button className="onboarding-back" onClick={() => setStep(1)}>← Back</button>
              <span>Step 2 of 2</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
