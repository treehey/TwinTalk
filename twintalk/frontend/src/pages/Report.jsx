import { useEffect, useState } from 'react'
import { getAgentReports, deleteAgentReport } from '../services/api'
import { BackIcon, TrashIcon } from '../icons'

/* Helper: consistent emoji avatar */
const getEmojiAvatar = (name) => {
  if (!name) return '🤖';
  const emojis = ['👽', '👾', '🚀', '🔮', '🎭', '⚡', '🔥', '🌟', '🧠', '👁️', '🎲', '🧩'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash += name.charCodeAt(i);
  return emojis[hash % emojis.length];
};

/* Helper: consistent gradient */
const getAvatarGradient = (name) => {
  if (!name) return 'linear-gradient(135deg, #e0e0e0 0%, #bdbdbd 100%)';
  const gradients = [
    'linear-gradient(135deg, #FFD02F 0%, #FF9800 100%)',
    'linear-gradient(135deg, #B2EBF2 0%, #80DEEA 100%)',
    'linear-gradient(135deg, #E1BEE7 0%, #CE93D8 100%)',
    'linear-gradient(135deg, #C8E6C9 0%, #81C784 100%)',
    'linear-gradient(135deg, #FFCDD2 0%, #EF9A9A 100%)',
    'linear-gradient(135deg, #FFF9C4 0%, #FFF176 100%)',
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash += name.charCodeAt(i);
  return gradients[hash % gradients.length];
};

/* Error Boundary wrapper */
function SafeReportDetail({ report, onBack, onDelete }) {
  let summaryData = {}
  try {
    if (!report || !report.summary) {
      summaryData = {}
    } else if (typeof report.summary === 'string') {
      const parsed = JSON.parse(report.summary)
      summaryData = parsed && typeof parsed === 'object' ? parsed : {}
    } else if (typeof report.summary === 'object') {
      summaryData = report.summary
    }
  } catch (e) {
    console.warn('Failed to parse report summary:', e)
    summaryData = {}
  }

  const title = summaryData.title || '对话分析报告'
  const summary = summaryData.summary || ''
  const commonGround = Array.isArray(summaryData.common_ground) ? summaryData.common_ground : []
  const divergence = Array.isArray(summaryData.divergence) ? summaryData.divergence : []
  const highlights = Array.isArray(summaryData.highlights) ? summaryData.highlights : []
  const matchAnalysis = summaryData.match_analysis || ''

  return (
    <div className="report-detail-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <button className="report-back-btn" onClick={onBack} style={{ marginBottom: 0 }}>
          <BackIcon /> 返回列表
        </button>
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => onDelete(report.id)}
          style={{ color: 'var(--c-danger)', display: 'flex', alignItems: 'center', gap: '4px' }}
        >
          <TrashIcon /> 删除
        </button>
      </div>

      {/* Gradient header */}
      <div className="report-detail-header">
        <div className="report-detail-emoji">📊</div>
        <h2 className="report-detail-title">{title}</h2>
        <div className="report-detail-participants">
          <span className="report-participant-chip">
            {report.owner_nickname || '某人'}
          </span>
          <span className="report-vs">✦</span>
          <span className="report-participant-chip">
            {report.partner_nickname || '某人'}
          </span>
        </div>
        <div className="report-detail-time">
          {report.created_at
            ? new Intl.DateTimeFormat('zh-CN', {
              timeZone: 'Asia/Shanghai',
              year: 'numeric', month: '2-digit', day: '2-digit',
              hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
            }).format(new Date(report.created_at))
            : ''}
        </div>
      </div>

      {/* Summary section */}
      {summary ? (
        <div className="report-section">
          <div className="report-section-header">
            <span className="report-section-icon">💬</span>
            <h3>总体总结</h3>
          </div>
          <p className="report-section-text">{summary}</p>
        </div>
      ) : (
        <div className="report-section">
          <div className="report-section-header">
            <span className="report-section-icon">⏳</span>
            <h3>报告内容</h3>
          </div>
          <p className="report-section-text" style={{ color: 'var(--c-text-secondary)' }}>
            报告数据为空或正在生成中，请稍后刷新查看。
          </p>
        </div>
      )}

      {/* Common ground */}
      {commonGround.length > 0 && (
        <div className="report-section">
          <div className="report-section-header">
            <span className="report-section-icon">🤝</span>
            <h3>发现共同点</h3>
          </div>
          <ul className="report-tag-list">
            {commonGround.map((cg, i) => (
              <li key={i} className="report-tag-item report-tag-green">{String(cg)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Divergence */}
      {divergence.length > 0 && (
        <div className="report-section">
          <div className="report-section-header">
            <span className="report-section-icon">⚡</span>
            <h3>视角分歧</h3>
          </div>
          <ul className="report-tag-list">
            {divergence.map((dg, i) => (
              <li key={i} className="report-tag-item report-tag-orange">{String(dg)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Highlights */}
      {highlights.length > 0 && (
        <div className="report-section">
          <div className="report-section-header">
            <span className="report-section-icon">✨</span>
            <h3>金句摘录</h3>
          </div>
          <div className="report-quotes">
            {highlights.map((hl, i) => (
              <blockquote key={i} className="report-quote">{String(hl)}</blockquote>
            ))}
          </div>
        </div>
      )}

      {/* Match analysis */}
      {matchAnalysis && (
        <div className="report-section report-section-match">
          <div className="report-section-header">
            <span className="report-section-icon">💡</span>
            <h3>匹配度评价</h3>
          </div>
          <p className="report-match-text">{matchAnalysis}</p>
        </div>
      )}
    </div>
  )
}


export default function Report({ isActive }) {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedReport, setSelectedReport] = useState(null)
  const [renderError, setRenderError] = useState(null)

  const fetchReports = () => {
    setLoading(true)
    setError(null)
    getAgentReports()
      .then(res => {
        setReports(res.reports || [])
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  const handleDelete = async (e, reportId) => {
    if (e) e.stopPropagation()
    if (!window.confirm("确定要删除这篇对话报告吗？")) return;

    try {
      await deleteAgentReport(reportId)
      if (selectedReport && selectedReport.id === reportId) {
        setSelectedReport(null)
      }
      fetchReports()
    } catch (err) {
      alert("删除失败: " + err.message)
    }
  }

  // Re-fetch every time the page becomes active
  useEffect(() => {
    if (isActive) {
      fetchReports()
    }
  }, [isActive])

  // Also fetch on initial mount
  useEffect(() => {
    fetchReports()
  }, [])

  // If detail view crashes, show a fallback
  if (renderError) {
    return (
      <div className="report-list-page">
        <div className="report-error">
          <span>⚠️</span>
          <p>报告渲染出错: {renderError}</p>
          <button className="btn btn-primary btn-sm" onClick={() => {
            setRenderError(null)
            setSelectedReport(null)
          }}>返回列表</button>
        </div>
      </div>
    )
  }

  if (selectedReport) {
    try {
      return (
        <SafeReportDetail
          report={selectedReport}
          onBack={() => setSelectedReport(null)}
          onDelete={(id) => handleDelete(null, id)}
        />
      )
    } catch (e) {
      console.error('Report detail render error:', e)
      setRenderError(e.message)
      return null
    }
  }

  return (
    <div className="report-list-page">
      {/* Page header */}
      <div className="report-page-header">
        <div className="report-page-header-icon">📋</div>
        <div>
          <h2 className="report-page-title">Agent 对谈报告</h2>
          <p className="report-page-subtitle">AI 孪生体自主对话的深度分析</p>
        </div>
      </div>

      {loading ? (
        <div className="report-loading">
          <div className="loading-dots"><span /><span /><span /></div>
          <p>加载报告中...</p>
        </div>
      ) : error ? (
        <div className="report-error">
          <span>⚠️</span>
          <p>加载失败: {error}</p>
          <button className="btn btn-primary btn-sm" onClick={fetchReports}>重试</button>
        </div>
      ) : reports.length === 0 ? (
        <div className="report-empty">
          <div className="report-empty-icon">📝</div>
          <h3>暂无报告</h3>
          <p>在首页推荐用户卡片上点击「Agent对谈」，<br />让两个 AI 孪生体自由聊天并生成分析报告！</p>
        </div>
      ) : (
        <div className="report-list">
          {reports.map(report => {
            let title = ''
            try {
              if (report.summary && typeof report.summary === 'string') {
                const parsed = JSON.parse(report.summary)
                if (parsed && typeof parsed === 'object') {
                  title = parsed.title || ''
                }
              }
            } catch (e) { /* ignore parse errors */ }

            return (
              <button key={report.id} className="report-list-card" onClick={() => setSelectedReport(report)}>
                <div className="report-list-card-left">
                  <div
                    className="report-list-card-avatar"
                    style={{
                      background: getAvatarGradient(report.partner_nickname),
                      color: '#111',
                      fontSize: '20px',
                      border: 'none',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                    }}
                  >
                    {getEmojiAvatar(report.partner_nickname)}
                  </div>
                </div>
                <div className="report-list-card-body">
                  <div className="report-list-card-title">
                    与 {report.partner_nickname || '未知用户'} 的对谈
                  </div>
                  {title && <div className="report-list-card-subtitle">{title}</div>}
                  <div className="report-list-card-time">
                    {report.created_at
                      ? new Intl.DateTimeFormat('zh-CN', {
                        timeZone: 'Asia/Shanghai',
                        year: 'numeric', month: '2-digit', day: '2-digit',
                        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
                      }).format(new Date(report.created_at))
                      : ''}
                  </div>
                </div>
                <button
                  className="btn btn-icon btn-sm"
                  onClick={(e) => handleDelete(e, report.id)}
                  title="删除报告"
                  style={{ color: 'var(--c-text-secondary)', zIndex: 2 }}
                >
                  <TrashIcon />
                </button>
                <div className="report-list-card-arrow">›</div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
