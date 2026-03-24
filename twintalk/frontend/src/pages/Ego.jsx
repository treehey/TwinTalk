import { useEffect, useRef, useState } from 'react'
import { getDmStats, getMyProfile, sendMessage, addMemory, getAlignmentQuestions, submitAlignmentAnswers, syncDmMemory, getMirrorGreeting, listMemories, deleteMemory, editMemory } from '../services/api'
import { SendIcon } from '../icons'

/* ── MOCK TRAITS FOR VISUAL CLOUD (Fallback) ── */
const MOCK_TRAITS = [
  { text: "INTP 架构师", size: 'large', color: '#9D85FF', top: '45%', left: '35%' },
  { text: "咖啡重度依赖", size: 'medium', color: '#FF9E8A', top: '40%', left: '70%' },
  { text: "夜间创作者", size: 'small', color: '#10b981', top: '65%', left: '25%' },
  { text: "极简主义", size: 'medium', color: '#f59e0b', top: '65%', left: '75%' },
  { text: "科技流", size: 'large', color: '#3b82f6', top: '25%', left: '50%' },
  { text: "播客听众", size: 'small', color: '#8b5cf6', top: '80%', left: '50%' },
  { text: "理性先行", size: 'medium', color: '#ec4899', top: '30%', left: '20%' },
]

/* ── Dynamic Trait Generator ── */
const COLORS = ['#9D85FF', '#FF9E8A', '#10b981', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f43f5e', '#14b8a6', '#a855f7', '#fb923c', '#22d3ee', '#a3e635'];
const POSITIONS = [
  { top: 50, left: 50 }, // Center
  { top: 32, left: 50 }, // R1 Top
  { top: 60, left: 32 }, // R1 Bottom L
  { top: 60, left: 68 }, // R1 Bottom R
  { top: 12, left: 50 }, // R2 Top
  { top: 22, left: 82 }, // R2 Top R
  { top: 50, left: 88 }, // R2 Mid R
  { top: 78, left: 82 }, // R2 Bottom R
  { top: 88, left: 50 }, // R2 Bottom
  { top: 78, left: 18 }, // R2 Bottom L
  { top: 50, left: 12 }, // R2 Mid L
  { top: 22, left: 18 }, // R2 Top L
];

function generateDynamicTraits(profile) {
  if (!profile) return MOCK_TRAITS;

  const items = [];
  const extra = profile.extra_info || {};

  if (extra.mbti) items.push({ text: extra.mbti, weight: 3 });
  if (Array.isArray(extra.personality_keywords)) {
    extra.personality_keywords.forEach(kw => items.push({ text: kw, weight: 2 }));
  }
  if (Array.isArray(profile.interests)) {
    profile.interests.slice(0, 10).forEach(int => items.push({ text: int, weight: 2 }));
  }
  if (profile.values_profile && Array.isArray(profile.values_profile['核心价值'])) {
    profile.values_profile['核心价值'].slice(0, 5).forEach(v => items.push({ text: v, weight: 3 }));
  }
  if (profile.communication_style && profile.communication_style['风格']) {
    items.push({ text: profile.communication_style['风格'], weight: 1 });
  }

  // Deduplicate by text
  const uniqueMap = new Map();
  items.forEach(item => {
    if (!uniqueMap.has(item.text)) uniqueMap.set(item.text, item);
  });
  const uniqueItems = Array.from(uniqueMap.values()).slice(0, 12);

  if (uniqueItems.length === 0) return [];

  return uniqueItems.map((item, index) => {
    const size = item.weight >= 3 ? 'large' : item.weight === 2 ? 'medium' : 'small';
    const color = COLORS[index % COLORS.length];
    
    const basePos = POSITIONS[index % POSITIONS.length];
    const top = `${basePos.top}%`;
    const left = `${basePos.left}%`;

    return { text: item.text, size, color, top, left };
  });
}

/* ── TraitCloud (Section 1) ──────────────────────────── */
function TraitCloud({ fitnessIndex, profile }) {
  const syncRate = fitnessIndex || 50
  const activeTraits = generateDynamicTraits(profile)
  
  return (
    <div className="ego-section trait-cloud-section">
      <div className="section-yellow-header ego-header-block">
        <div className="section-yellow-title">个人画像</div>
        <div style={{ fontSize: '13px', color: '#111111', fontWeight: 500 }}>
          当前拟合度 <strong style={{ color: '#111111', fontSize: '18px', fontWeight: 800 }}>{syncRate}%</strong>
        </div>
      </div>
      
      {/* Memory Summary */}
      {profile?.memory_summary && (
        <div style={{
          margin: '12px 16px 0',
          padding: '10px 14px',
          background: 'rgba(157,133,255,0.08)',
          borderRadius: '10px',
          fontSize: '12px',
          lineHeight: '1.6',
          color: 'var(--c-text-secondary)',
        }}>
          <span style={{ fontWeight: 600, color: 'var(--c-text-primary)', marginRight: '6px' }}>📝 记忆摘要</span>
          {profile.memory_summary.length > 120
            ? profile.memory_summary.slice(0, 120) + '...'
            : profile.memory_summary
          }
        </div>
      )}

      <div className="trait-canvas" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {activeTraits.length > 0 ? activeTraits.map(t => (
          <div
            key={t.text}
            className={`trait-bubble size-${t.size}`}
            style={{
              '--bubble-color': t.color,
              top: t.top,
              left: t.left,
              animationDelay: `${Math.random() * 2}s`
            }}
          >
            {t.text}
          </div>
        )) : (
          <div style={{ textAlign: 'center', color: 'var(--c-text-secondary)', padding: '20px', maxWidth: '80%' }}>
            <p style={{ fontSize: '15px', marginBottom: '8px' }}>✨ 你的 Ego Matrix 虚位以待</p>
            <p style={{ fontSize: '13px', opacity: 0.8 }}>点击右上角设置图标，选择你想要展示的个性气泡，或者多跟 Agent 聊聊来发掘更多特质。</p>
          </div>
        )}
      </div>

      <div className="scroll-down-hint">
        <span>上滑与本我对谈</span>
        <div className="chevron-down" />
      </div>
    </div>
  )
}

function MirrorChat({ setHideNav, onChatUpdate }) {
  const [messages, setMessages] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sessionId] = useState(`mirror_${Date.now()}`)
  const bottomRef = useRef(null)
  
  // Note: For full fullscreen immersion, we can optionally hide nav on focus.
  const handleFocus = () => setHideNav?.(true)
  const handleBlur = () => setHideNav?.(false)

  // Fetch proactive greeting on mount
  useEffect(() => {
    let mounted = true
    const initGreeting = async () => {
      setSending(true)
      try {
        const res = await getMirrorGreeting(sessionId)
        if (mounted) {
          setMessages([{ role: 'assistant', content: res.reply || '嗨，我是你的数字孪生。今天有什么想梳理的心绪吗？' }])
          setSuggestions(res.suggestions || [])
        }
      } catch (err) {
        if (mounted) {
          setMessages([{ role: 'assistant', content: '嗨，我是你的数字孪生。今天有什么想梳理的心绪吗？' }])
        }
      } finally {
        if (mounted) setSending(false)
      }
    }
    initGreeting()
    return () => { mounted = false }
  }, [sessionId])

  useEffect(() => {
    if (messages.length > 0 && bottomRef.current) {
      const container = bottomRef.current.parentElement
      if (container) {
        container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' })
      }
    }
  }, [messages, suggestions])

  const handleSuggestionClick = (text) => {
    setSuggestions([])
    handleSend(text)
  }

  const handleSend = async (overrideText) => {
    const text = typeof overrideText === 'string' ? overrideText : input.trim()
    if (!text || sending) return
    const newMessages = [...messages, { role: 'user', content: text }]
    setMessages(newMessages)
    setInput('')
    setSuggestions([])
    setSending(true)
    try {
      const data = await sendMessage(text, sessionId, 'mirror_test')
      setMessages([...newMessages, { role: 'assistant', content: data.reply || '...' }])
      if (onChatUpdate) {
        setTimeout(() => onChatUpdate(), 500)
      }
    } catch (err) {
      setMessages([...newMessages, { role: 'assistant', content: `出错了: ${err.message}` }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="ego-section mirror-chat-section">
      <div className="mirror-shell" style={{ height: '100%', borderRadius: 0, border: 'none' }}>
        <div style={{
          padding: '16px',
          background: 'var(--c-bg)',
          fontSize: '12px',
          color: 'var(--c-text-secondary)',
          textAlign: 'center',
          boxShadow: '0 4px 12px rgba(0,0,0,0.03)'
        }}>
          与内心的声音对话，完善你的隐藏特质。
        </div>

        <div className="mirror-messages" style={{ paddingBottom: '20px' }}>
          {messages.map((msg, i) => (
            <div key={i} className={`mirror-msg-row ${msg.role === 'user' ? 'user-row' : ''}`}>
              <div className={`mirror-avatar ${msg.role === 'assistant' ? 'ai-avatar' : 'user-avatar'}`}>
                {msg.role === 'assistant' ? 'AI' : '我'}
              </div>
              <div
                className={`chat-bubble ${msg.role === 'user' ? 'user' : 'assistant'}`}
                style={{ maxWidth: '76%' }}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {sending && (
            <div className="mirror-msg-row">
              <div className="mirror-avatar ai-avatar">AI</div>
              <div className="chat-bubble assistant" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div className="loading-dots"><span /><span /><span /></div>
                <span style={{ fontSize: '13px', color: 'var(--c-text-secondary)' }}>正在思考...</span>
              </div>
            </div>
          )}
          
          {suggestions.length > 0 && !sending && (
            <div className="mirror-suggestions" style={{ display: 'flex', flexDirection: 'column', gap: '10px', padding: '8px 16px 20px', alignItems: 'center' }}>
              {suggestions.map((sug, i) => (
                <button
                  key={i}
                  className="mirror-suggestion-btn"
                  onClick={() => handleSuggestionClick(sug)}
                >
                  {sug}
                </button>
              ))}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div className="chat-input-bar">
          <input
            type="text"
            placeholder="写点真实的想法..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSend() }}
            onFocus={handleFocus}
            onBlur={handleBlur}
            disabled={sending}
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={sending || !input.trim()}
            aria-label="发送"
          >
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── MemoryList — view, edit, delete existing memories ── */
function MemoryList({ memories, onRefresh, showToast }) {
  const [editingId, setEditingId] = useState(null)
  const [editText, setEditText] = useState('')
  const [deleting, setDeleting] = useState(null)

  const handleDelete = async (id) => {
    setDeleting(id)
    try {
      await deleteMemory(id)
      showToast?.('✅ 记忆已删除')
      onRefresh()
    } catch (err) {
      showToast?.(err.message)
    } finally {
      setDeleting(null)
    }
  }

  const handleSaveEdit = async (id) => {
    if (!editText.trim()) return
    try {
      await editMemory(id, { content: editText.trim() })
      showToast?.('✅ 记忆已更新')
      setEditingId(null)
      setEditText('')
      onRefresh()
    } catch (err) {
      showToast?.(err.message)
    }
  }

  const typeLabel = (t) => {
    const map = { user_added: '手动', system_extracted: '系统', chat_extracted: '对话', platform_generated: '平台' }
    return map[t] || t
  }

  if (!memories || memories.length === 0) {
    return (
      <div style={{ textAlign: 'center', color: 'var(--c-text-secondary)', padding: '20px', fontSize: '13px' }}>
        暂无记忆条目，试试与 Agent 对话或手动录入。
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {memories.map(m => (
        <div key={m.id} style={{
          padding: '10px 12px',
          borderRadius: '8px',
          background: 'var(--c-card-bg, #fff)',
          border: '1px solid var(--c-border)',
          fontSize: '13px',
        }}>
          {editingId === m.id ? (
            <div>
              <textarea
                className="form-textarea"
                rows={2}
                value={editText}
                onChange={e => setEditText(e.target.value)}
                style={{ marginBottom: '8px', fontSize: '13px' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn btn-primary btn-sm" style={{ flex: 1 }} onClick={() => handleSaveEdit(m.id)}>保存</button>
                <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => setEditingId(null)}>取消</button>
              </div>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                <div style={{ flex: 1, lineHeight: '1.5', wordBreak: 'break-word' }}>{m.content}</div>
                <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                  <button
                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '14px', padding: '2px' }}
                    title="编辑"
                    onClick={() => { setEditingId(m.id); setEditText(m.content) }}
                  >✏️</button>
                  <button
                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '14px', padding: '2px', opacity: deleting === m.id ? 0.4 : 1 }}
                    title="删除"
                    disabled={deleting === m.id}
                    onClick={() => handleDelete(m.id)}
                  >🗑️</button>
                </div>
              </div>
              <div style={{ marginTop: '4px', display: 'flex', gap: '8px', fontSize: '11px', color: 'var(--c-text-secondary)' }}>
                <span style={{ background: 'rgba(157,133,255,0.12)', borderRadius: '4px', padding: '1px 6px' }}>{typeLabel(m.memory_type)}</span>
                <span>重要度 {(m.importance_score || 0.5).toFixed(1)}</span>
                {m.tags?.length > 0 && <span>{m.tags.join(', ')}</span>}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

/* ── CalibrationPanel (Section 3 - Settings/Alignment) ─ */
function CalibrationPanel({ showToast, onSynced, onScoreChange }) {
  const [syncing, setSyncing] = useState(false)
  const [memoryInput, setMemoryInput] = useState('')
  const [syncingDm, setSyncingDm] = useState(false)
  const [memories, setMemories] = useState([])
  const [loadingMem, setLoadingMem] = useState(false)
  const [showMemories, setShowMemories] = useState(false)

  const loadMemories = async () => {
    setLoadingMem(true)
    try {
      const res = await listMemories()
      setMemories(res.memories || [])
    } catch (_) {}
    setLoadingMem(false)
  }

  useEffect(() => {
    if (showMemories) loadMemories()
  }, [showMemories])

  const handleRefresh = () => {
    loadMemories()
    onSynced()
  }

  return (
    <div className="ego-section calibration-section" style={{ padding: '24px 16px', background: 'var(--c-bg)' }}>
      <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', textAlign: 'center' }}>数据与记忆管理</h3>
      
      {/* Manual memory input */}
      <div className="mobile-card" style={{ boxShadow: 'none', border: '1px solid var(--c-border)' }}>
        <h4 style={{ fontSize: '14px', marginBottom: '8px' }}>手动录入记忆</h4>
        <textarea
          className="form-textarea"
          rows={2}
          placeholder="例如：我非常讨厌香菜..."
          value={memoryInput}
          onChange={(e) => setMemoryInput(e.target.value)}
          style={{ marginBottom: '10px' }}
        />
        <button
          className="btn btn-primary btn-sm"
          style={{ width: '100%' }}
          disabled={syncing || !memoryInput.trim()}
          onClick={async () => {
            setSyncing(true)
            try {
              await addMemory(memoryInput.trim())
              showToast?.('✅ 记忆同步成功！')
              setMemoryInput('')
              handleRefresh()
            } catch (err) {
              showToast?.(err.message)
            } finally {
              setSyncing(false)
            }
          }}
        >
          {syncing ? '同步中...' : '提交同步'}
        </button>
      </div>

      {/* DM sync */}
      <div className="mobile-card" style={{ boxShadow: 'none', border: '1px solid var(--c-border)', marginTop: '12px' }}>
        <h4 style={{ fontSize: '14px', marginBottom: '8px' }}>同步私信记忆</h4>
        <button
          className="btn btn-secondary btn-sm"
          style={{ width: '100%' }}
          disabled={syncingDm}
          onClick={async () => {
            setSyncingDm(true)
            try {
              const result = await syncDmMemory()
              showToast?.(`✅ 已同步 ${result.synced || 0} 条私信记忆`)
              handleRefresh()
            } catch (err) {
              showToast?.(err.message)
            } finally {
              setSyncingDm(false)
            }
          }}
        >
          {syncingDm ? '同步中...' : '一键提取私信记忆'}
        </button>
      </div>

      {/* Memory list toggle */}
      <div className="mobile-card" style={{ boxShadow: 'none', border: '1px solid var(--c-border)', marginTop: '12px' }}>
        <div
          style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            cursor: 'pointer', userSelect: 'none',
          }}
          onClick={() => setShowMemories(!showMemories)}
        >
          <h4 style={{ fontSize: '14px', margin: 0 }}>
            已有记忆 {memories.length > 0 && <span style={{ fontWeight: 400, color: 'var(--c-text-secondary)' }}>({memories.length})</span>}
          </h4>
          <span style={{ fontSize: '18px', transform: showMemories ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>▾</span>
        </div>

        {showMemories && (
          <div style={{ marginTop: '12px' }}>
            {loadingMem ? (
              <div style={{ textAlign: 'center', color: 'var(--c-text-secondary)', padding: '12px', fontSize: '13px' }}>加载中...</div>
            ) : (
              <MemoryList memories={memories} onRefresh={handleRefresh} showToast={showToast} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Ego (main export) ───────────────────────────────── */
export default function Ego({ setHideNav, showToast }) {
  const [profile, setProfile] = useState(null)
  const [fitnessIndex, setFitnessIndex] = useState(50)
  const [manualBoost, setManualBoost] = useState(0)

  const reloadProfile = () => {
    getMyProfile()
      .then((data) => {
        setProfile(data.profile || null)
        setFitnessIndex(data.fitness_index || 50)
      })
      .catch(() => {})
  }

  useEffect(() => { reloadProfile() }, [])

  return (
    <div className="ego-page-scroll">
      {/* Section 1: Trait Cloud */}
      <TraitCloud 
        fitnessIndex={fitnessIndex + manualBoost} 
        profile={profile} 
      />
      
      {/* Section 2: Full Screen Chat Flow */}
      <MirrorChat setHideNav={setHideNav} onChatUpdate={reloadProfile} />
      
      {/* Section 3: Data Management */}
      <CalibrationPanel 
        showToast={showToast} 
        onSynced={reloadProfile}
        onScoreChange={(delta) => setManualBoost((v) => v + delta)}
      />
    </div>
  )
}
