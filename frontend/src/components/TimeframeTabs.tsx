type View = 'today' | 'tomorrow' | 'week'

interface Props {
  active: View
  todayCount: number
  tomorrowCount: number
  onChange: (v: View) => void
}

export function TimeframeTabs({ active, todayCount, tomorrowCount, onChange }: Props) {
  return (
    <div className="tf-tabs fade-in d1">
      <button className={`tf-tab ${active === 'today' ? 'active' : ''}`} onClick={() => onChange('today')}>
        Today <span className="tf-badge">{todayCount}</span>
      </button>
      <button className={`tf-tab ${active === 'tomorrow' ? 'active' : ''}`} onClick={() => onChange('tomorrow')}>
        Tomorrow <span className="tf-badge">{tomorrowCount}</span>
      </button>
      <button className={`tf-tab ${active === 'week' ? 'active' : ''}`} onClick={() => onChange('week')}>
        This week
      </button>
    </div>
  )
}
