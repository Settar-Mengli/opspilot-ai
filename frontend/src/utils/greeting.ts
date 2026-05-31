export type TimeOfDay = 'morning' | 'afternoon' | 'evening' | 'night'

export function getTimeOfDay(hour?: number): TimeOfDay {
  const h = hour ?? new Date().getHours()
  if (h >= 5 && h < 12) return 'morning'
  if (h >= 12 && h < 17) return 'afternoon'
  if (h >= 17 && h < 22) return 'evening'
  return 'night'
}

export function getGreetingWord(timeOfDay: TimeOfDay): string {
  switch (timeOfDay) {
    case 'morning':
      return 'Good morning'
    case 'afternoon':
      return 'Good afternoon'
    case 'evening':
      return 'Good evening'
    case 'night':
      return 'Working late'
  }
}
