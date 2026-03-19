import { useState, useEffect } from 'react'
import { isLoggedIn, logout, getMe } from './services/api'
import Onboarding from './pages/Onboarding'
import World from './pages/World'
import Ego from './pages/Ego'
import { HomeIcon, UserIcon } from './icons'
import './index.css'

const NAV_ITEMS = [
  { key: 'world', label: '世界', Icon: HomeIcon },
  { key: 'ego',   label: '本我', Icon: UserIcon  },
]

const PAGE_TITLES = {
  world: 'TwinTalk · 世界',
  ego:   'TwinTalk · 本我',
}

export default function App() {
  const [user, setUser] = useState(null)
  const [page, setPage] = useState('world')
  const [loading, setLoading] = useState(true)
  // hiddenNav is set to true by child pages (e.g. DM chat) that need full-screen
  const [hiddenNav, setHiddenNav] = useState(false)

  useEffect(() => {
    if (isLoggedIn()) {
      getMe()
        .then((data) => setUser(data.user))
        .catch(() => logout())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const handleLogin = (userData) => {
    setUser(userData)
    setPage('world')
  }

  if (loading) {
    return (
      <div className="onboarding-container">
        <div className="loading-dots"><span /><span /><span /></div>
      </div>
    )
  }

  if (!user || !user.onboarding_completed) {
    return <Onboarding onLogin={handleLogin} />
  }

  const handleLogout = () => {
    logout()
    setUser(null)
  }

  return (
    <div className="mobile-app">
      {/* ── Fixed Header ── */}
      {!hiddenNav && (
        <header className="mobile-header">
          <button className="icon-btn" onClick={handleLogout} aria-label="退出登录" title="退出">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </button>
          <span className="mobile-header-title">Social</span>
          <button className="icon-btn" aria-label="Compose new post">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
        </header>
      )}

      {/* ── Scrollable Content ── */}
      <main className="mobile-main">
        {page === 'world'
          ? <World onHideNav={setHiddenNav} />
          : <Ego />}
      </main>

      {/* ── Bottom Navigation ── */}
      {!hiddenNav && (
        <nav className="mobile-bottom-nav">
          {NAV_ITEMS.map(({ key, label, Icon }) => (
            <button
              key={key}
              className={`mobile-nav-item ${page === key ? 'active' : ''}`}
              onClick={() => setPage(key)}
              aria-label={label}
            >
              <Icon active={page === key} />
              <span className="mobile-nav-label">{label}</span>
            </button>
          ))}
        </nav>
      )}
    </div>
  )
}
