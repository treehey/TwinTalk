import { useState, useEffect, useCallback } from 'react'
import { getMe, isLoggedIn, logout, listDmConversations } from './services/api'
import Onboarding from './pages/Onboarding'
import Social from './pages/Social'
import World from './pages/World'
import Ego from './pages/Ego'
import { HomeIcon, MessageIcon, UserIcon, LogoutIcon, MagicActionIcon } from './icons'

/* ── Toast Component ── */
function Toast({ message, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 2800)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className="toast-notification">
      <span>{message}</span>
    </div>
  )
}

/* ── App ── */
export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // 3-Tab state: 'social', 'ego'
  const [page, setPage] = useState('social')
  const [hideNav, setHideNav] = useState(false)
  const [totalUnread, setTotalUnread] = useState(0)
  const [toasts, setToasts] = useState([])

  // Drawer / Bottom sheet state
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [agentMenuOpen, setAgentMenuOpen] = useState(false)

  // ── Global toast helper ──
  const showToast = useCallback((msg) => {
    const id = Date.now()
    setToasts((prev) => [...prev, { id, message: msg }])
  }, [])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  // ── Auth bootstrapping ──
  useEffect(() => {
    if (!isLoggedIn()) { setLoading(false); return }
    getMe()
      .then((data) => setUser(data.user))
      .catch(() => { logout(); setUser(null) })
      .finally(() => setLoading(false))
  }, [])

  // ── Unread count polling ──
  useEffect(() => {
    if (!user) return
    const fetchUnread = () => {
      listDmConversations()
        .then((data) => {
          const sum = (data.conversations || []).reduce((a, c) => a + (c.unread_count || 0), 0)
          setTotalUnread(sum)
        })
        .catch(() => {})
    }
    fetchUnread()
    const interval = setInterval(fetchUnread, 15000)
    return () => clearInterval(interval)
  }, [user])

  const [pendingDmTargetId, setPendingDmTargetId] = useState(null)

  // ── Handler for "start DM from Social card" ──
  const handleStartDm = (targetUserId) => {
    setDrawerOpen(true)
    setPendingDmTargetId(targetUserId)
  }

  if (loading) {
    return (
      <div className="mobile-app">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100dvh' }}>
          <div className="loading-dots"><span /><span /><span /></div>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Onboarding onLogin={(u) => { setUser(u); setPage('social') }} />
  }

  return (
    <div className="mobile-app">
      {/* ── Top Header ── */}
      {!hideNav && (
        <header className="mobile-header" style={{ justifyContent: 'space-between' }}>
          {/* Left: Inbox Drawer Toggle */}
          <button className="header-icon-btn" onClick={() => setDrawerOpen(true)} aria-label="消息">
            <MessageIcon />
            {totalUnread > 0 && (
              <span className="header-badge">{totalUnread > 99 ? '99+' : totalUnread}</span>
            )}
          </button>

          {/* Center: TwinTalk Artistic Logo */}
          <div className="twintalk-logo" style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)' }}>
            TwinTalk
          </div>

          {/* Right: Logout */}
          <button
            className="header-icon-btn"
            onClick={() => { logout(); setUser(null) }}
            aria-label="退出"
          >
            <LogoutIcon />
          </button>
        </header>
      )}

      {/* ── Main Content Area ── */}
      <main className="mobile-main">
        <div className={`page-container ${page === 'social' ? 'page-active' : 'page-hidden'}`}>
          <Social onStartDm={handleStartDm} />
        </div>
        <div className={`page-container ${page === 'ego' ? 'page-active' : 'page-hidden'}`}>
          <Ego
            setHideNav={setHideNav}
            showToast={showToast}
          />
        </div>
      </main>

      {/* ── Left Drawer (Inbox) ── */}
      <div className={`overlay-backdrop ${drawerOpen ? 'open' : ''}`} onClick={() => setDrawerOpen(false)} />
      <div className={`left-drawer ${drawerOpen ? 'open' : ''}`}>
        {/* World.jsx is now acting purely as the inbox content inside the drawer */}
        <World
          setHideNav={setHideNav}
          showToast={showToast}
          onUnreadChange={setTotalUnread}
          pendingDmTargetId={pendingDmTargetId}
          onDmStarted={() => setPendingDmTargetId(null)}
          isActive={drawerOpen}
        />
      </div>

      {/* ── Radial Agent Menu Overlay ── */}
      <div className={`overlay-backdrop ${agentMenuOpen ? 'open' : ''}`} onClick={() => setAgentMenuOpen(false)} style={{ zIndex: 100 }} />
      
      <div className={`radial-menu-wrapper ${agentMenuOpen ? 'open' : ''}`}>
        <button className="radial-item advisor" onClick={() => { showToast('Advisor (情感顾问) 功能即将上线'); setAgentMenuOpen(false); }}>
          <div className="icon" style={{ color: '#10b981' }}>A</div>
          <span>Advisor</span>
        </button>
        <button className="radial-item planner" onClick={() => { showToast('Planner (规划师) 功能即将上线'); setAgentMenuOpen(false); }}>
          <div className="icon" style={{ color: '#f59e0b' }}>P</div>
          <span>Planner</span>
        </button>
      </div>

      {/* ── Bottom Navigation Bar (3 Tabs) ── */}
      {!hideNav && (
        <nav className="mobile-bottom-nav">
          <button
            className={`nav-tab ${page === 'social' ? 'active' : ''}`}
            onClick={() => setPage('social')}
          >
            <span className="nav-tab-icon"><HomeIcon active={page === 'social'} /></span>
          </button>
          
          <button
            className={`nav-tab nav-tab-action ${agentMenuOpen ? 'active-menu' : ''}`}
            onClick={() => setAgentMenuOpen(!agentMenuOpen)}
          >
            <span className="nav-tab-icon"><MagicActionIcon /></span>
          </button>
          
          <button
            className={`nav-tab ${page === 'ego' ? 'active' : ''}`}
            onClick={() => setPage('ego')}
          >
            <span className="nav-tab-icon"><UserIcon active={page === 'ego'} /></span>
          </button>
        </nav>
      )}

      {/* ── Toast Container ── */}
      <div className="toast-container">
        {toasts.map((t) => (
          <Toast key={t.id} message={t.message} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </div>
  )
}
