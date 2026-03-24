import { useEffect, useState } from 'react'
import { findMatches, followUser, unfollowUser, getFollowing, startDmConversation, startAgentChat } from '../services/api'

// Helper: generate consistent emoji avatar
const getEmojiAvatar = (name) => {
  if (!name) return '🤖';
  const emojis = ['👽', '👾', '🚀', '🔮', '🎭', '⚡', '🔥', '🌟', '🧠', '👁️', '🎲', '🧩'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash += name.charCodeAt(i);
  return emojis[hash % emojis.length];
};

// Helper: extract short phrase tags from bio string
const extractTags = (bio, interests) => {
  const tags = new Set([...(interests || [])]);
  if (bio) {
    const phrases = bio.split(/[,，。；;、\n]/).map(s => s.trim()).filter(s => s.length >= 2 && s.length <= 8);
    phrases.forEach(p => tags.add(p));
  }
  return Array.from(tags).slice(0, 5); // Return up to 5 cohesive tags
};

/* ── MatchCard – post-style layout ─────────────────── */
function MatchCard({ match, onStartDm, showToast, style }) {
  const [agentStarting, setAgentStarting] = useState(false)


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

  // Pick a gradient for the card hero based on name seed
  const gradients = [
    'linear-gradient(135deg, #FFD02F 0%, #FF9800 100%)',
    'linear-gradient(135deg, #B2EBF2 0%, #80DEEA 100%)',
    'linear-gradient(135deg, #E1BEE7 0%, #CE93D8 100%)',
    'linear-gradient(135deg, #C8E6C9 0%, #81C784 100%)',
    'linear-gradient(135deg, #FFCDD2 0%, #EF9A9A 100%)',
    'linear-gradient(135deg, #FFF9C4 0%, #FFF176 100%)',
  ]
  const nicknameHash = (match.user.nickname || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  const heroGradient = gradients[nicknameHash % gradients.length]

  const scorePercent = Math.round((match.score || 0) * 100)
  const bio = match.bio_third_view || ''
  const tags = match.profile_tags || extractTags(bio, match.common_interests)
  const matchReason = match.match_reason || ''

  return (
    <article className="post-card" style={{ ...style, padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Hero header with gradient */}
      <div style={{ background: heroGradient, padding: '28px 20px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
        {/* Large avatar */}
        <div style={{ width: '80px', height: '80px', borderRadius: '50%', background: 'rgba(255,255,255,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '44px', backdropFilter: 'blur(4px)', boxShadow: '0 4px 16px rgba(0,0,0,0.1)' }}>
          {getEmojiAvatar(match.user.nickname)}
        </div>

        {/* Name */}
        <div style={{ fontSize: '22px', fontWeight: 800, color: '#111111', letterSpacing: '-0.3px' }}>
          {match.user.nickname}
        </div>

        {/* Match score badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(0,0,0,0.12)', borderRadius: '100px', padding: '4px 14px' }}>
          <div style={{ width: '80px', height: '4px', background: 'rgba(0,0,0,0.15)', borderRadius: '2px', overflow: 'hidden' }}>
            <div style={{ width: `${scorePercent}%`, height: '100%', background: '#111111', borderRadius: '2px' }} />
          </div>
          <span style={{ fontSize: '13px', fontWeight: 800, color: '#111111' }}>{scorePercent}% 匹配</span>
        </div>
      </div>

      {/* Card body */}
      <div style={{ flex: 1, padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '14px', overflowY: 'auto' }}>

        {/* Common interests count */}
        {match.common_interests?.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            <span style={{ fontSize: '15px', color: '#757575' }}>共同兴趣</span>
            <span style={{ fontWeight: 700, color: '#111111', fontSize: '15px' }}>{match.common_interests.length} 项</span>
          </div>
        )}

        {/* Match Reason */}
        {matchReason && (
          <div style={{
            flexShrink: 0,
            fontSize: '15px',
            color: '#111',
            lineHeight: '1.6',
            background: 'linear-gradient(135deg, #FFF8E1, #FFFDE7)',
            borderRadius: '12px',
            padding: '10px 14px',
            borderLeft: '3px solid #FFD02F',
            fontWeight: 500
          }}>
            💡 {matchReason}
          </div>
        )}

        {/* Bio excerpt */}
        {bio.length > 0 && (
          <div style={{ 
            flexShrink: 0,
            fontSize: '15px', 
            color: '#555', 
            lineHeight: '1.6',
            background: '#F8F9FA',
            borderRadius: '12px',
            padding: '12px 14px',
            whiteSpace: 'pre-wrap'
          }}>
            {bio}
          </div>
        )}

        {/* Tags */}
        {tags.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', flexShrink: 0 }}>
            {tags.map((tag, idx) => (
              <span key={idx} style={{ background: '#F2F2F2', color: '#333', fontWeight: 600, padding: '6px 14px', borderRadius: '100px', fontSize: '13px' }}>
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Footer actions */}
      <div style={{ padding: '12px 20px 20px', display: 'flex', gap: '10px' }}>
        <button
          className="btn"
          style={{
            flex: 1,
            background: 'transparent',
            border: '1.5px solid #111111',
            borderRadius: '100px',
            color: '#111111',
            fontWeight: 600,
            padding: '12px 0',
            fontSize: '16px'
          }}
          onClick={() => onStartDm(match.user.id)}
        >
          发私信
        </button>
        <button
          className="btn"
          style={{
            flex: 1,
            background: '#FFD02F',
            border: 'none',
            borderRadius: '100px',
            color: '#111111',
            fontWeight: 700,
            padding: '12px 0',
            fontSize: '16px'
          }}
          onClick={handleAgentChat}
          disabled={agentStarting}
        >
          {agentStarting ? '启动中...' : 'Agent对谈'}
        </button>
      </div>

    </article>
  )
}

/* ── Stacked Deck Swipe View ──────────────────────── */
function StackedDeck({ matches, onStartDm, followingSet, setFollowingSet, showToast }) {
  const [activeIndex, setActiveIndex] = useState(0)
  const [dragX, setDragX] = useState(0)
  const [startX, setStartX] = useState(0)
  const [isDragging, setIsDragging] = useState(false)

  const handleDragStart = (clientX) => {
    setStartX(clientX)
    setIsDragging(true)
  }

  const handleDragMove = (clientX) => {
    if (!isDragging) return
    setDragX(clientX - startX)
  }

  const handleDragEnd = () => {
    if (!isDragging) return
    setIsDragging(false)
    if (dragX < -60) {
      if (activeIndex < matches.length - 1) setActiveIndex(activeIndex + 1)
    } else if (dragX > 60) {
      if (activeIndex > 0) setActiveIndex(activeIndex - 1)
    }
    setDragX(0)
  }

  const onTouchStart = (e) => handleDragStart(e.touches[0].clientX)
  const onTouchMove = (e) => handleDragMove(e.touches[0].clientX)
  const onTouchEnd = () => handleDragEnd()

  const onMouseDown = (e) => handleDragStart(e.clientX)
  const onMouseMove = (e) => handleDragMove(e.clientX)
  const onMouseUp = () => handleDragEnd()
  const onMouseLeave = () => { if (isDragging) handleDragEnd() }

  if (matches.length === 0) return null;

  return (
    <div 
      style={{ position: 'relative', flex: 1, padding: '16px', overflow: 'hidden', height: 'calc(100vh - 200px)', userSelect: 'none' }}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseLeave}
    >
      {matches.map((match, i) => {
        const offset = i - activeIndex;
        if (offset < -2 || offset > 2) return null; // Render sides

        const screenW = Math.min(window.innerWidth, 500);
        const CARD_WIDTH = screenW * 0.75; // Narrower card to show edges
        const PITCH = screenW * 0.78;      // Spacing between cards

        const baseTranslateX = offset * PITCH;
        // Apply dragX to ALL cards proportionally
        const finalTranslateX = baseTranslateX + (isDragging ? dragX : 0);

        // Scale down as it moves away from center
        const maxDist = PITCH;
        const dist = Math.abs(finalTranslateX);
        const scale = Math.max(0.9, 1 - (dist / maxDist) * 0.1);
        const opacity = 1; // Side cards should be fully visible like the image

        return (
           <div 
             key={match.user.id}
             style={{
               position: 'absolute',
               top: 0,
               bottom: 40,
               left: '50%',
               marginLeft: -(CARD_WIDTH / 2),
               width: CARD_WIDTH,
               transform: `translateX(${finalTranslateX}px) scale(${scale})`,
               zIndex: 100 - Math.abs(offset),
               opacity: opacity,
               transition: isDragging ? 'none' : 'all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1)',
               transformOrigin: 'center center'
             }}
           >
             <MatchCard 
               style={{ height: '100%', margin: 0, display: 'flex', flexDirection: 'column' }} 
               match={match} 
               isFollowing={followingSet.has(match.user.id)}
               onFollowChange={() => {
                 const newSet = new Set(followingSet)
                 if (newSet.has(match.user.id)) newSet.delete(match.user.id)
                 else newSet.add(match.user.id)
                 setFollowingSet(newSet)
               }}
               onStartDm={onStartDm}
               showToast={showToast}
             />
           </div>
        )
      })}
    </div>
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
      // Verify matches are sorted by score descending
      const sorted = [...(data.matches || [])].sort((a,b) => (b.score || 0) - (a.score || 0));
      setMatches(sorted)
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
      <div className="section-yellow-header">
        <div className="section-yellow-title">为你推荐</div>
        <button
          className="btn btn-sm"
          style={{ 
            borderRadius: '100px', 
            background: '#111111', 
            color: '#FFFFFF', 
            border: 'none',
            fontWeight: 600,
            padding: '6px 16px',
            height: '32px',
            minHeight: '32px'
          }}
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
        <StackedDeck 
          matches={matches} 
          onStartDm={onStartDm} 
          followingSet={followingSet} 
          setFollowingSet={setFollowingSet} 
          showToast={showToast} 
        />
      )}
    </div>
  )
}
