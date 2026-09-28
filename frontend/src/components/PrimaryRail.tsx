import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  List,
  Eye,
  FileText,
  Plug,
  Settings,
} from 'lucide-react'

const TOP = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/items', label: 'All Items', icon: List },
  { to: '/insights', label: 'Insights', icon: Eye },
  { to: '/briefing', label: 'Briefing', icon: FileText },
] as const

const BOTTOM = [
  { to: '/connections', label: 'Connections', icon: Plug },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const

function RailLink({
  to,
  label,
  icon: Icon,
}: {
  to: string
  label: string
  icon: typeof LayoutDashboard
}) {
  return (
    <NavLink
      to={to}
      className="desk-rail-btn"
      aria-label={label}
      title={label}
      end={to === '/dashboard'}
    >
      <Icon size={20} strokeWidth={2} aria-hidden />
      <span className="tip">{label}</span>
    </NavLink>
  )
}

export function PrimaryRail() {
  return (
    <nav className="desk-rail" aria-label="Primary">
      <div className="desk-rail-group">
        {TOP.map((item) => (
          <RailLink key={item.to} {...item} />
        ))}
      </div>
      <div className="desk-rail-group">
        {BOTTOM.map((item) => (
          <RailLink key={item.to} {...item} />
        ))}
      </div>
    </nav>
  )
}
