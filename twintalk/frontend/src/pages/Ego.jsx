import { useEffect, useRef, useState } from 'react'
import { getDmStats, getMyProfile, sendMessage, addMemory, getAlignmentQuestions, submitAlignmentAnswers, syncDmMemory } from '../services/api'
import { SendIcon } from '../icons'

/* ── MOCK TRAITS FOR VISUAL CLOUD ── */
const MOCK_TRAITS = [
  { text: "INTP 架构师", size: 'large', color: '#9D85FF', top: '10%', left: '10%' },
  { text: "咖啡重度依赖", size: 'medium', color: '#FF9E8A', top: '25%', left: '60%' },
  { text: "夜间创作者", size: 'small', color: '#10b981', top: '50%', left: '15%' },
  { text: "极简主义", size: 'medium', color: '#f59e0b', top: '40%', left: '50%' },
  { text: "科技流", size: 'large', color: '#3b82f6', top: '70%', left: '30%' },
  { text: "播客听众", size: 'small', color: '#8b5cf6', top: '80%', left: '70%' },
  { text: "理性先行", size: 'medium', color: '#ec4899', top: '15%', left: '80%' },
]

/* ── TraitCloud (Section 1) ──────────────────────────── */
function TraitCloud({ fitnessIndex }) {
  const syncRate = fitnessIndex || 50
  
  return (
    <div className="ego-section trait-cloud-section">
      <div className="ego-header-block">
        <h2 style={{ fontSize: '28px', fontWeight: 800, fontFamily: '"Times New Roman", serif', fontStyle: 'italic', letterSpacing: '1px' }}>Ego Matrix</h2>
        <div style={{ fontSize: '13px', color: 'var(--c-text-secondary)', marginTop: '8px' }}>
          当前拟合度 <strong style={{ color: 'var(--c-accent)', fontSize: '18px' }}>{syncRate}%</strong>
        </div>
      </div>
      
      <div className="trait-canvas">
        {MOCK_TRAITS.map(t => (
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
        ))}
      </div>

      <div className="scroll-down-hint">
        <span>上滑与本我对谈</span>
        <div className="chevron-down" />
      </div>
    </div>
  )
}

/* ── MirrorChat (Section 2) ──────────────────────────── */
function MirrorChat({ setHideNav }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '嗨，我是你的数字孪生。在这里我们可以进行一场深层自我对谈。最近有什么想梳理的思绪，或是平时不常表现出来的真实想法吗？' }
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sessionId] = useState(`mirror_${Date.now()}`)
  const bottomRef = useRef(null)
  
  // Note: For full fullscreen immersion, we can optionally hide nav on focus.
  const handleFocus = () => setHideNav?.(true)
  const handleBlur = () => setHideNav?.(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || sending) return
    const newMessages = [...messages, { role: 'user', content: text }]
    setMessages(newMessages)
    setInput('')
    setSending(true)
    try {
      const data = await sendMessage(text, sessionId, 'mirror_test')
      setMessages([...newMessages, { role: 'assistant', content: data.reply || '...' }])
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

/* ── CalibrationPanel (Section 3 - Settings/Alignment) ─ */
function CalibrationPanel({ showToast, onSynced, onScoreChange }) {
  const [syncing, setSyncing] = useState(false)
  const [memoryInput, setMemoryInput] = useState('')
  const [syncingDm, setSyncingDm] = useState(false)

  // Only keeping the memory sync blocks to save space and keep it clean, 
  // alignment questions can be loaded similarly if needed.

  return (
    <div className="ego-section calibration-section" style={{ padding: '24px 16px', background: 'var(--c-bg)' }}>
      <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', textAlign: 'center' }}>数据与记忆管理</h3>
      
      <div className="mobile-card" style={{ boxShadow: 'none', border: '1px solid var(--c-border)' }}>
        <h4 style={{ fontSize: '14px', marginBottom: '8px' }}>📝 手动录入记忆</h4>
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
              onSynced()
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

      <div className="mobile-card" style={{ boxShadow: 'none', border: '1px solid var(--c-border)', marginTop: '12px' }}>
        <h4 style={{ fontSize: '14px', marginBottom: '8px' }}>💬 同步私信记忆</h4>
        <button
          className="btn btn-secondary btn-sm"
          style={{ width: '100%' }}
          disabled={syncingDm}
          onClick={async () => {
            setSyncingDm(true)
            try {
              const result = await syncDmMemory()
              showToast?.(`✅ 已同步 ${result.synced || 0} 条私信记忆`)
              onSynced()
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
      <TraitCloud fitnessIndex={fitnessIndex + manualBoost} />
      
      {/* Section 2: Full Screen Chat Flow */}
      <MirrorChat setHideNav={setHideNav} />
      
      {/* Section 3: Data Management */}
      <CalibrationPanel 
        showToast={showToast} 
        onSynced={reloadProfile}
        onScoreChange={(delta) => setManualBoost((v) => v + delta)}
      />
    </div>
  )
}
