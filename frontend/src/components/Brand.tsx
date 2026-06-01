import { Link } from 'react-router-dom'

export function Brand() {
  return (
    <Link to="/dashboard" className="brand">
      <div className="brand-name">Ops<em>Pilot</em></div>
      <span className="brand-tag">AI</span>
    </Link>
  )
}
