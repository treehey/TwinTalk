import { useEffect, useState } from 'react'
import { findMatches, followUser, unfollowUser, getFollowing, startDmConversation, startAgentChat } from '../services/api'

/* ── MatchCard – post-style layout ─────────────────── */
function MatchCard({ match, onStartDm, isFollowing, onFollowChange, showToast }) {
  const [following, setFollowing] = useState(isFollowing)
  const [loading, setLoading] = useState(false)
  const [agentStarting, setAgentStarting] = useState(false)

  const avatarLetter = (match.user.nickname || '匿').trim().slice(0, 1).toUpperCase()

  const handleFollow = async () => {
    setLoading(true)
    try {
      if (following) {
        await unfollowUser(match.user.id)
        setFollowing(false)
      } else {
        await followUser(match.user.id)
        setFollowing(true)
      }
      onFollowChange?.()
    } catch (error) {
      console.error('关注操作失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAgentChat = async () => {
    if (!window.confirm("确定开始系统模拟你与此人的对话吗？大约需要1分钟生成最终报告。")) return
    setAgentStarting(true)
    try {
      if (showToast) showToast('正在初始化特工对谈...')
      const convRes = await startDmConversation(match.user.id)
      await startAgentChat(convRes.conversation.id)
      if (showToast) showToast('Agent 会话已在后台愉快地进行中！\n稍后可去 Report 页面查看。')
    } catch (error) {
      console.error(error)
      if (showToast) showToast('启动失败: ' + error.message)
    } finally {
      setAgentStarting(false)
    }
  }

  return (
    <article className="post-card">
      {/* Post-style header: avatar + name + meta */}
      <div className="post-card-header">
        <div className="post-avatar">{avatarLetter}</div>
        <div className="post-user-info">
          <span className="post-user-name">{match.user.nickname}</span>
          <span className="post-user-meta">
            共同兴趣 {match.common_count || 0} 项 · 匹配度 {Math.round((match.score || 0) * 100)}%
          </span>
        </div>
        {/* Follow button in top-right */}
        <button
          className={`btn btn-sm ${following ? 'btn-secondary' : 'btn-primary'}`}
          style={{ borderRadius: 'var(--radius-full)', flexShrink: 0 }}
          onClick={handleFollow}
          disabled={loading}
        >
          {following ? '已关注' : '关注'}
        </button>
      </div>

      {/* Bio */}
      {match.bio_third_view && (
        <div className="post-content">{match.bio_third_view}</div>
      )}

      {/* Interest tags */}
      {match.common_interests && match.common_interests.length > 0 && (
        <div className="twin-interests" style={{ marginBottom: '12px' }}>
          {match.common_interests.slice(0, 5).map((interest) => (
            <span key={interest} className="interest-tag">{interest}</span>
          ))}
          {match.common_interests.length > 5 && (
            <span className="interest-tag" style={{ background: 'transparent', color: 'var(--c-text-secondary)' }}>
              +{match.common_interests.length - 5}
            </span>
          )}
        </div>
      )}

      {/* Post actions: DM button & Agent autochat button */}
      <div className="post-actions">
        <button
          className="dm-chat-btn"
          onClick={() => onStartDm(match.user.id)}
          aria-label="私信"
        >
          {/* Chat icon */}
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
          </svg>
          发私信
        </button>

        <button
          className="agent-chat-btn"
          onClick={handleAgentChat}
          disabled={agentStarting}
          aria-label="Agent 对谈"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="10" rx="2" />
            <circle cx="9" cy="16" r="1" fill="currentColor" />
            <circle cx="15" cy="16" r="1" fill="currentColor" />
            <path d="M8 11V7a4 4 0 0 1 8 0v4" />
            <path d="M12 2v1" />
            <path d="M19 5l-1 1" />
            <path d="M5 5l1 1" />
          </svg>
          {agentStarting ? '启动中...' : 'Agent对谈'}
        </button>
      </div>
    </article>
  )
}


/* ── Social ─────────────────────────────────────────── */
export default function Social({ onStartDm, showToast }) {
  const [matches, setMatches] = useState([])
  const [followingSet, setFollowingSet] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshToken, setRefreshToken] = useState('init')

  // Load following IDs from backend on mount
  useEffect(() => {
    getFollowing()
      .then((data) => setFollowingSet(new Set(data.following_ids || [])))
      .catch(() => {})
  }, [])

  const loadMatches = async (token = refreshToken) => {
    try {
      setLoading(true)
      const data = await findMatches(20, token)
      setMatches(data.matches || [])
      setError(null)
    } catch (err) {
      console.error('加载匹配用户失败:', err)
      setError(err.message || '加载失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadMatches(refreshToken) }, [refreshToken])

  if (loading) {
    return (
      <div className="empty-state">
        <div className="loading-dots"><span /><span /><span /></div>
        <p style={{ marginTop: '12px' }}>正在为你匹配...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="empty-state">
        <p style={{ color: 'var(--text-error)' }}>⚠️ {error}</p>
        <button className="btn btn-primary" onClick={() => loadMatches()} style={{ marginTop: '16px' }}>重试</button>
      </div>
    )
  }

  return (
    <div>
      {/* Header bar */}
      <div style={{
        padding: '14px 16px',
        borderBottom: '1px solid var(--c-border)',
        background: 'var(--c-bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--c-text-primary)' }}>🎯 为你推荐</div>
          <div style={{ fontSize: '12px', color: 'var(--c-text-secondary)', marginTop: '2px' }}>基于兴趣、性格、价值观综合匹配</div>
        </div>
        <button
          className="btn btn-secondary btn-sm"
          style={{ borderRadius: 'var(--radius-full)' }}
          onClick={() => setRefreshToken(String(Date.now()))}
        >
          换一批
        </button>
      </div>

      {/* Match list */}
      {matches.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">🌐</span>
          <h3>暂无推荐用户</h3>
          <p>先完善你的画像，让算法更了解你。</p>
          <button className="btn btn-primary" onClick={() => loadMatches()}>重新加载</button>
        </div>
      ) : (
        <div className="social-grid">
          {matches.map((match) => (
            <MatchCard
              key={match.user.id}
              match={match}
              onStartDm={onStartDm}
              isFollowing={followingSet.has(match.user.id)}
              onFollowChange={() => setFollowingSet((prev) => new Set(prev))}
              showToast={showToast}
            />
          ))}
        </div>
      )}
    </div>
  )
}
