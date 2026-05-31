import { useCallback, useEffect, useRef, useState } from 'react'

// TypeScript doesn't know about the Web Speech API by default
// because it's not in the standard DOM types yet. We declare what we need.
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
  resultIndex: number
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string
  message: string
}

interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  onend: (() => void) | null
  onstart: (() => void) | null
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognitionInstance
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
}

function getRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

export function isSpeechRecognitionSupported(): boolean {
  return getRecognitionConstructor() !== null
}

export interface SpeechRecognitionState {
  supported: boolean
  listening: boolean
  transcript: string
  interimTranscript: string
  error: string | null
}

export interface SpeechRecognitionControls {
  start: () => void
  stop: () => void
  cancel: () => void
  reset: () => void
}

export function useSpeechRecognition(options?: {
  lang?: string
  onFinalTranscript?: (transcript: string) => void
}): SpeechRecognitionState & SpeechRecognitionControls {
  const lang = options?.lang ?? 'en-US'
  const onFinalTranscriptRef = useRef(options?.onFinalTranscript)

  useEffect(() => {
    onFinalTranscriptRef.current = options?.onFinalTranscript
  })

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)
  const cancelledRef = useRef(false)
  const [supported] = useState<boolean>(() => isSpeechRecognitionSupported())
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [interimTranscript, setInterimTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Create the recognition instance once if supported.
  useEffect(() => {
    if (!supported) return
    const Ctor = getRecognitionConstructor()
    if (!Ctor) return

    const recognition = new Ctor()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = lang

    recognition.onstart = () => {
      setListening(true)
      setError(null)
    }

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalText = ''
      let interimText = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        const text = result[0].transcript
        if (result.isFinal) {
          finalText += text
        } else {
          interimText += text
        }
      }
      if (finalText) {
        setTranscript(prev => prev + finalText)
      }
      setInterimTranscript(interimText)
    }

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const code = event.error || 'unknown'
      let friendly = 'Voice input is not available right now.'
      if (code === 'not-allowed' || code === 'service-not-allowed') {
        friendly = 'Microphone access is blocked. Enable it in your browser settings.'
      } else if (code === 'no-speech') {
        friendly = 'I did not catch anything. Try again.'
      } else if (code === 'network') {
        friendly = 'Speech recognition needs network access. Check your connection.'
      } else if (code === 'audio-capture') {
        friendly = 'No microphone detected.'
      }
      setError(friendly)
      setListening(false)
    }

    recognition.onend = () => {
      setListening(false)
      setInterimTranscript('')
      if (cancelledRef.current) {
        // User explicitly cancelled — discard captured text, do not fire callback
        setTranscript('')
        cancelledRef.current = false
        return
      }
      // Pull the final transcript at end so we don't fire callbacks mid-stream
      setTranscript(current => {
        const finalText = current.trim()
        if (finalText && onFinalTranscriptRef.current) {
          // Fire the callback async to let state settle
          queueMicrotask(() => {
            onFinalTranscriptRef.current?.(finalText)
          })
        }
        return current
      })
    }

    recognitionRef.current = recognition
    return () => {
      try {
        recognition.abort()
      } catch {
        // ignore
      }
      recognitionRef.current = null
    }
  }, [supported, lang])

  const start = useCallback(() => {
    if (!recognitionRef.current || listening) return
    cancelledRef.current = false
    setTranscript('')
    setInterimTranscript('')
    setError(null)
    try {
      recognitionRef.current.start()
    } catch {
      // start() throws if already running; ignore
    }
  }, [listening])

  const stop = useCallback(() => {
    if (!recognitionRef.current) return
    try {
      recognitionRef.current.stop()
    } catch {
      // ignore
    }
  }, [])

  const cancel = useCallback(() => {
    if (!recognitionRef.current) return
    cancelledRef.current = true
    try {
      recognitionRef.current.abort()
    } catch {
      // ignore
    }
  }, [])

  const reset = useCallback(() => {
    setTranscript('')
    setInterimTranscript('')
    setError(null)
  }, [])

  return {
    supported,
    listening,
    transcript,
    interimTranscript,
    error,
    start,
    stop,
    cancel,
    reset,
  }
}
