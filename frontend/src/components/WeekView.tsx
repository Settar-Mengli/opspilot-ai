const DAYS = [
  { name: 'Mon', num: 1, items: ['Board deck review', '1:1 with CTO'] },
  { name: 'Tue', num: 2, items: ['Board meeting · 10 AM', 'Q2 close · finance'], today: true },
  { name: 'Wed', num: 3, items: ['All-hands prep'] },
  { name: 'Thu', num: 4, items: [] as string[] },
  { name: 'Fri', num: 5, items: ['Weekly review · 4 PM'] },
]

export function WeekView() {
  return (
    <div className="week-grid fade-in d3">
      {DAYS.map(day => (
        <div key={day.name} className={`week-day ${'today' in day && day.today ? 'today' : ''}`}>
          <div className="day-head">
            <span className="day-name">{day.name}{'today' in day && day.today ? ' · Big day' : ''}</span>
            <span className="day-num">{day.num}</span>
          </div>
          <div className="day-items">
            {day.items.length === 0
              ? <div className="day-empty">No items yet</div>
              : day.items.map((item, i) => (
                <div key={i} className={`day-item ${'today' in day && day.today ? 'high' : ''}`}>{item}</div>
              ))
            }
          </div>
        </div>
      ))}
    </div>
  )
}
