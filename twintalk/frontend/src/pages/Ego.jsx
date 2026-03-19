import { useEffect, useMemo, useRef, useState } from 'react'
import { getDmStats, getMyProfile, sendMessage, addMemory, getAlignmentQuestions, submitAlignmentAnswers } from '../services/api'
import { SendIcon } from '../icons'

/* ── LabOverview ─────────────────────────────────────── */
function LabOverview({ stats, fitnessIndex, onGoCalibration }) {
  const syncRate = fitnessIndex || 50

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px' }}>
      {/* Fitness card */}
      <div className="mobile-card">
        <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '12px', color: 'var(--c-text-primary)' }}>
          构造空间
        </h3>
        <div style={{ fontSize: '14px', marginBottom: '6px', color: 'var(--c-text-secondary)' }}>
          拟合度指数：<strong style={{ color: 'var(--c-text-primary)', fontSize: '20px' }}>{syncRate}%</strong>
        </div>
        <div className="progress-bar" style={{ marginBottom: '8px' }}>
          <div className="progress-fill" style={{ width: `${syncRate}%` }} />
        </div>
        <p style={{ fontSize: '13px', color: 'var(--c-text-secondary)', lineHeight: 1.6 }}>
          {syncRate >= 85
            ? '拟合度较高，建议通过私信场景继续微调"价值观边界"。'
            : '当前拟合度仍可提升，建议补充问卷与关键记忆。'}
        </p>
        <div style={{ marginTop: '12px', fontSize: '13px', color: 'var(--c-text-secondary)', paddingTop: '10px', borderTop: '1px solid var(--c-border)' }}>
          本周发送私信 <strong>{stats.sent_messages_week}</strong> 条
        </div>
      </div>

      {/* CTA to calibration */}
      <button
        className="btn btn-primary"
        style={{ width: '100%', borderRadius: 'var(--radius-md)' }}
        onClick={onGoCalibration}
      >
        前往画像维系 →
      </button>
    </div>
  )
}

/* ── CalibrationPanel ────────────────────────────────── */
function CalibrationPanel({ onSynced, onScoreChange }) {
  const [syncing, setSyncing] = useState(false)
  const [memoryInput, setMemoryInput] = useState('')
  const [answers, setAnswers] = useState({})
  const [questions, setQuestions] = useState([])
  const [loadingQs, setLoadingQs] = useState(true)

  useEffect(() => {
    getAlignmentQuestions()
      .then(res => setQuestions(res.questions || []))
      .catch(err => alert('无法加载对齐问题：' + err.message))
      .finally(() => setLoadingQs(false))
  }, [])

  const completed = questions.length > 0 && questions.every((q) => answers[q.id])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px' }}>
      {/* Memory Sync */}
      <div className="mobile-card">
        <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '8px', color: 'var(--c-text-primary)' }}>同步记忆</h3>
        <p style={{ fontSize: '13px', color: 'var(--c-text-secondary)', marginBottom: '12px', lineHeight: 1.6 }}>
          输入一段与你相关的记忆事件或事实，数字分身将把它纳入核心认知中。
        </p>
        <textarea
          className="form-textarea"
          rows={3}
          placeholder="例如：我非常讨厌香菜，吃火锅一定要点毛肚..."
          value={memoryInput}
          onChange={(e) => setMemoryInput(e.target.value)}
          style={{ marginBottom: '10px' }}
        />
        <button
          className="btn btn-primary"
          style={{ width: '100%' }}
          disabled={syncing || !memoryInput.trim()}
          onClick={async () => {
            setSyncing(true)
            try {
              await addMemory(memoryInput.trim())
              alert('记忆同步成功！')
              setMemoryInput('')
              onSynced()
            } catch (err) {
              alert(err.message)
            } finally {
              setSyncing(false)
            }
          }}
        >
          {syncing ? '同步中...' : '提交同步'}
        </button>
      </div>

      {/* Alignment Questions */}
      <div className="mobile-card">
        <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '10px', color: 'var(--c-text-primary)' }}>人格对齐</h3>
        {loadingQs ? (
          <div style={{ padding: '20px', textAlign: 'center' }}>
            <div className="loading-dots"><span /><span /><span /></div>
            <p style={{ marginTop: '10px', fontSize: '13px', color: 'var(--c-text-secondary)' }}>正在生成专属对齐问题...</p>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {questions.map((q) => (
                <div key={q.id}>
                  <div style={{ fontSize: '14px', color: 'var(--c-text-primary)', marginBottom: '8px', lineHeight: 1.5 }}>{q.title}</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {(q.options || []).map((opt) => (
                      <button
                        key={opt}
                        className={`btn btn-sm ${answers[q.id] === opt ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ borderRadius: 'var(--radius-full)' }}
                        onClick={() => setAnswers((prev) => ({ ...prev, [q.id]: opt }))}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <button
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '16px' }}
              disabled={!completed || syncing}
              onClick={async () => {
                setSyncing(true)
                try {
                  const payload = questions.map(q => ({ title: q.title, choice: answers[q.id] }))
                  await submitAlignmentAnswers(payload)
                  alert('已学习你的决策逻辑')
                  onScoreChange(30)
                  onSynced()
                  setAnswers({})
                  setQuestions([])
                  setLoadingQs(true)
                  getAlignmentQuestions()
                    .then(res => setQuestions(res.questions || []))
                    .finally(() => setLoadingQs(false))
                } catch (err) {
                  alert(err.message)
                } finally {
                  setSyncing(false)
                }
              }}
            >
              {syncing ? '提交中...' : '提交对齐'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}

/* ── MirrorPanel (full-screen chat) ─────────────────── */
function MirrorPanel() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '嗨，我是你的数字孪生。在这里我们可以进行一场深层自我对谈。最近有什么想梳理的思绪，或是平时不常表现出来的真实想法吗？' }
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sessionId] = useState(`mirror_${Date.now()}`)
  const bottomRef = useRef(null)

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
    <div className="mirror-shell" style={{ height: '100%' }}>
      {/* Header info strip */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--c-border)',
        background: 'var(--c-bg)',
        fontSize: '12px',
        color: 'var(--c-text-secondary)',
        lineHeight: 1.5,
      }}>
        与你的专属 AI 孪生对谈，它会主动挖掘你的人格特征并存入记忆库。
      </div>

      {/* Messages */}
      <div className="mirror-messages">
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

      {/* Input bar */}
      <div className="chat-input-bar">
        <input
          type="text"
          placeholder="写点真实的想法..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSend() }}
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
  )
}

/* ── Ego (main export) ───────────────────────────────── */
export default function Ego() {
  const [tab, setTab] = useState('lab')
  const [profile, setProfile] = useState(null)
  const [fitnessIndex, setFitnessIndex] = useState(50)
  const [stats, setStats] = useState({ sent_messages_week: 0 })
  const [manualBoost, setManualBoost] = useState(0)

  const reloadProfile = () => {
    Promise.all([getMyProfile(), getDmStats()])
      .then(([profileData, statsData]) => {
        setProfile(profileData.profile || null)
        setFitnessIndex(profileData.fitness_index || 50)
        setStats({ sent_messages_week: statsData.sent_messages_week || 0 })
      })
      .catch(() => {
        setProfile(null)
        setFitnessIndex(50)
        setStats({ sent_messages_week: 0 })
      })
  }

  useEffect(() => { reloadProfile() }, [])

  const isMirror = tab === 'mirror'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Sticky segmented control */}
      <div style={{
        padding: '12px 16px',
        background: 'var(--c-bg)',
        borderBottom: '1px solid var(--c-border)',
        position: 'sticky',
        top: 0,
        zIndex: 5,
      }}>
        <div className="seg-control">
          <button className={`seg-btn ${tab === 'lab' ? 'active' : ''}`} onClick={() => setTab('lab')}>构造室</button>
          <button className={`seg-btn ${tab === 'calibration' ? 'active' : ''}`} onClick={() => setTab('calibration')}>画像维系</button>
          <button className={`seg-btn ${tab === 'mirror' ? 'active' : ''}`} onClick={() => setTab('mirror')}>镜像测试</button>
        </div>
      </div>

      {/* Content area – mirror gets full remaining height */}
      <div style={{ flex: 1, overflow: isMirror ? 'hidden' : 'auto', display: 'flex', flexDirection: 'column' }}>
        {tab === 'lab' && (
          <LabOverview
            stats={stats}
            fitnessIndex={fitnessIndex + manualBoost}
            onGoCalibration={() => setTab('calibration')}
          />
        )}
        {tab === 'calibration' && (
          <CalibrationPanel
            onSynced={reloadProfile}
            onScoreChange={(delta) => setManualBoost((v) => v + delta)}
          />
        )}
        {tab === 'mirror' && <MirrorPanel />}
      </div>
    </div>
  )
}
