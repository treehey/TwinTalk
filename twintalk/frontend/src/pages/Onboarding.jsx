import { useState, useEffect } from 'react'
import {
  login,
  register,
  getOnboardingQuestionnaire,
  getQuestionnaire,
  submitAnswers,
  buildProfile,
  completeOnboarding,
} from '../services/api'

// ─── Step 1: Register / Login ─────────────────────────────────────────────────
function LoginStep({ onDone }) {
  const [tab, setTab] = useState('login')   // 'login' | 'register'
  const [phoneNumber, setPhoneNumber] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      let data
      if (tab === 'register') {
        if (!phoneNumber.trim()) { setError('请输入手机号'); setLoading(false); return }
        if (password.length < 6) { setError('密码不能少于 6 位'); setLoading(false); return }
        data = await register(phoneNumber.trim(), password)
      } else {
        if (!phoneNumber.trim() || !password) { setError('请输入手机号和密码'); setLoading(false); return }
        data = await login(phoneNumber.trim(), password)
      }
      onDone(data?.user || {})
    } catch (err) {

      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const tabStyle = (t) => ({
    flex: 1,
    padding: '10px',
    border: 'none',
    borderBottom: tab === t ? '3px solid #111111' : '3px solid transparent',
    background: 'transparent',
    color: tab === t ? '#111111' : 'var(--text-muted)',
    borderRadius: 0,
    cursor: 'pointer',
    fontWeight: tab === t ? '700' : '400',
    fontSize: '13px',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    transition: 'all 0.15s',
    fontFamily: 'inherit',
  })

  return (
    <div className="onboarding-container">
      <div className="onboarding-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{
          background: 'var(--c-accent)',
          padding: '40px 20px 32px',
          marginBottom: '32px'
        }}>
          <h1 className="brand-font" style={{ fontSize: '42px', color: '#111111', margin: '0 0 12px 0' }}>TwinTalk</h1>
          <p className="subtitle" style={{ margin: 0, color: 'rgba(17, 17, 17, 0.7)' }}>
            「 让灵魂相遇在见面前 」
          </p>
        </div>

        <div style={{ padding: '0 32px 40px' }}>
          {/* Bauhaus Tabs */}
          <div style={{ display: 'flex', borderBottom: '2px solid var(--border-subtle)', marginBottom: '24px' }}>
            <button style={tabStyle('login')} onClick={() => { setTab('login'); setError('') }}>登录</button>
            <button style={tabStyle('register')} onClick={() => { setTab('register'); setError('') }}>注册</button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">手机号</label>
              <input
                className="form-input"
                type="text"
                placeholder="输入手机号..."
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">密码</label>
              <input
                className="form-input"
                type="password"
                placeholder="输入密码..."
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && (
              <p style={{ color: 'var(--accent-danger)', fontSize: '14px', marginBottom: '16px' }}>
                {error}
              </p>
            )}
            <button className="btn btn-primary btn-lg" type="submit" disabled={loading} style={{ width: '100%' }}>
              {loading
                ? <span className="loading-dots"><span /><span /><span /></span>
                : tab === 'register' ? '注册并开始 →' : '登录 →'}
            </button>
          </form>
          <p style={{ marginTop: '24px', fontSize: '15px', color: 'var(--text-muted)' }}>
          数字孪生驱动的社交新范式
          </p>
        </div>
      </div>
    </div>
  )
}

// ─── Step 2: Onboarding questionnaire (inline, card-by-card) ─────────────────
function QuestionnaireStep({ user, onDone }) {
  const [questionnaire, setQuestionnaire] = useState(null)
  const [questions, setQuestions] = useState([])
  const [current, setCurrent] = useState(0)
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const q = await getOnboardingQuestionnaire()
        if (!q) { onDone(); return }
        const detail = await getQuestionnaire(q.id)
        setQuestionnaire(detail.questionnaire)
        setQuestions(detail.questionnaire.questions || [])
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const q = questions[current]
  const progress = questions.length > 0 ? ((current + 1) / questions.length) * 100 : 0

  const setAnswer = (val) => setAnswers((prev) => ({ ...prev, [q.id]: val }))
  const currentAnswer = q ? (answers[q.id] ?? '') : ''

  const handleNext = () => {
    if (current < questions.length - 1) {
      setCurrent((c) => c + 1)
    } else {
      handleSubmit()
    }
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const formatted = Object.entries(answers).map(([question_id, value]) => ({
        question_id,
        ...(typeof value === 'number' ? { scale_value: value } : { text_value: String(value) }),
      }))
      await submitAnswers(questionnaire.id, formatted)
      onDone()
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="onboarding-container">
        <div className="loading-dots"><span /><span /><span /></div>
      </div>
    )
  }

  if (!questionnaire || questions.length === 0) {
    return null
  }

  return (
    <div className="onboarding-container">
      <div className="onboarding-card" style={{ maxWidth: '560px' }}>
        {/* Header */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              认识你 · {current + 1} / {questions.length}
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {q?.dimension}
            </span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>

        {error && (
          <p style={{ color: 'var(--accent-danger)', fontSize: '14px', marginBottom: '16px' }}>
            {error}
          </p>
        )}

        {q && (
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '20px', lineHeight: 1.5 }}>
              {q.content}
            </h3>

            {/* Scale */}
            {q.question_type === 'scale' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  <span>{q.scale_min_label}</span>
                  <span>{q.scale_max_label}</span>
                </div>
                <input
                  type="range"
                  min={q.scale_min || 1}
                  max={q.scale_max || 7}
                  value={currentAnswer || Math.round(((q.scale_min || 1) + (q.scale_max || 7)) / 2)}
                  onChange={(e) => setAnswer(parseInt(e.target.value))}
                  style={{ width: '100%', accentColor: '#6366f1' }}
                />
                <div style={{ textAlign: 'center', marginTop: '8px', fontSize: '20px', fontWeight: '700', color: 'var(--accent-primary)' }}>
                  {currentAnswer || Math.round(((q.scale_min || 1) + (q.scale_max || 7)) / 2)}
                </div>
              </div>
            )}

            {/* Text */}
            {q.question_type === 'text' && (
              <textarea
                className="form-input"
                rows={3}
                placeholder={q.placeholder || '请输入...'}
                value={currentAnswer}
                onChange={(e) => setAnswer(e.target.value)}
                style={{ resize: 'vertical' }}
                autoFocus
              />
            )}

            {/* Single choice */}
            {q.question_type === 'choice' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {(Array.isArray(q.choices) ? q.choices : (typeof q.choices === 'string' ? JSON.parse(q.choices || '[]') : [])).map((choice) => (
                  <button
                    key={choice}
                    className={`btn ${currentAnswer === choice ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setAnswer(choice)}
                    style={{ textAlign: 'left', justifyContent: 'flex-start' }}
                  >
                    {currentAnswer === choice && '✓ '}{choice}
                  </button>
                ))}
              </div>
            )}

            {/* Multi choice */}
            {q.question_type === 'multi_choice' && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {(Array.isArray(q.choices) ? q.choices : (typeof q.choices === 'string' ? JSON.parse(q.choices || '[]') : [])).map((choice) => {
                  const selected = Array.isArray(currentAnswer) && currentAnswer.includes(choice)
                  return (
                    <button
                      key={choice}
                      className={`btn btn-sm ${selected ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => {
                        const prev = Array.isArray(currentAnswer) ? currentAnswer : []
                        setAnswer(selected ? prev.filter((c) => c !== choice) : [...prev, choice])
                      }}
                    >
                      {choice}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px', marginTop: '28px' }}>
          {current > 0 && (
            <button className="btn btn-ghost" onClick={() => setCurrent((c) => c - 1)}>
              ← 上一题
            </button>
          )}
          <button
            className="btn btn-primary"
            style={{ flex: 1 }}
            onClick={handleNext}
            disabled={submitting}
          >
            {submitting
              ? <span className="loading-dots"><span /><span /><span /></span>
              : current === questions.length - 1 ? '完成' : '下一题 →'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Step 3: Building profile ──────────────────────────────────────────────────
function BuildingStep({ onDone }) {
  const [error, setError] = useState('')

  useEffect(() => {
    async function build() {
      try {
        await buildProfile()
        await completeOnboarding()
        onDone()
      } catch (err) {
        setError(err.message)
      }
    }
    build()
  }, [])

  return (
    <div className="onboarding-container">
      <div className="glass-card onboarding-card" style={{ textAlign: 'center' }}>
        <h2 style={{ marginBottom: '12px' }}>正在构建你的数字分身…</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          AI 正在分析你的回答，生成专属画像
        </p>
        {error ? (
          <>
            <p style={{ color: 'var(--accent-danger)', marginBottom: '16px' }}>{error}</p>
            <button className="btn btn-primary" onClick={onDone}>跳过，稍后再说</button>
          </>
        ) : (
          <div className="loading-dots"><span /><span /><span /></div>
        )}
      </div>
    </div>
  )
}

// ─── Main Onboarding orchestrator ─────────────────────────────────────────────
export default function Onboarding({ onLogin }) {
  const [step, setStep] = useState('login')   // login | questionnaire | building
  const [user, setUser] = useState(null)

  const handleLoginDone = (userData) => {
    setUser(userData)
    // New users go through onboarding questionnaire; returning users skip
    if (!userData?.onboarding_completed) {
      setStep('questionnaire')
    } else {

      onLogin(userData)
    }
  }

  const handleQuestionnaireDone = () => {
    setStep('building')
  }

  const handleBuildingDone = () => {
    onLogin({ ...user, onboarding_completed: true })
  }

  if (step === 'login') return <LoginStep onDone={handleLoginDone} />
  if (step === 'questionnaire') return <QuestionnaireStep user={user} onDone={handleQuestionnaireDone} />
  if (step === 'building') return <BuildingStep onDone={handleBuildingDone} />
  return null
}
