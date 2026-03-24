import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  deleteDmConversation,
  getDmSuggestion,
  listDmConversations,
  listDmMessages,
  markDmRead,
  sendDmMessage,
  startDmConversation,
  startAgentChat,
} from '../services/api'
import { BackIcon, SendIcon } from '../icons'

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const now = new Date()
  const diffMs = now - d
  if (diffMs < 60000) return '刚刚'
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}分钟前`
  if (diffMs < 86400000) return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function getAvatarLabel(name) {
  if (!name) return '匿'
  return name.trim().slice(0, 1).toUpperCase()
}

/* ── DmInbox ─────────────────────────────────────────── */
function DmInbox({
  conversations,
  pinnedConversationIds,
  onOpenConversation,
  onTogglePinConversation,
  onDelete,
}) {
  const [searchKeyword, setSearchKeyword] = useState('')

  const filtered = useMemo(() => {
    const kw = searchKeyword.trim().toLowerCase()
    if (!kw) return conversations
    return conversations.filter((c) => {
      return (c.partner?.nickname || '').toLowerCase().includes(kw)
        || (c.source_community || '').toLowerCase().includes(kw)
        || (c.last_message || '').toLowerCase().includes(kw)
    })
  }, [conversations, searchKeyword])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const pinA = pinnedConversationIds.includes(a.id)
      const pinB = pinnedConversationIds.includes(b.id)
      if (pinA !== pinB) return pinA ? -1 : 1
      const unreadDiff = (b.unread_count || 0) - (a.unread_count || 0)
      if (unreadDiff !== 0) return unreadDiff
      return Date.parse(b.last_message_at || '') - Date.parse(a.last_message_at || '')
    })
  }, [filtered, pinnedConversationIds])

  return (
    <div className="dm-inbox-shell">
      {/* Toolbar */}
      <div className="dm-inbox-toolbar">
        <input
          className="dm-inbox-search"
          type="text"
          placeholder="搜索联系人 / 消息"
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
        />
      </div>

      <div className="dm-inbox-list">
        {sorted.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">✉️</span>
            <h3>{conversations.length === 0 ? '还没有私信' : '没有匹配结果'}</h3>
            <p>{conversations.length === 0
              ? '去首页推荐用户页面发起第一次私信吧！'
              : '试试更换关键词，或清空搜索。'}</p>
          </div>
        ) : (
          sorted.map((conv) => {
            const name = conv.partner?.nickname || '未命名'
            const isPinned = pinnedConversationIds.includes(conv.id)
            return (
              <div key={conv.id} className="dm-inbox-item-wrap">
                <button
                  className="dm-inbox-item"
                  onClick={() => onOpenConversation(conv)}
                  type="button"
                >
                  <div className="dm-inbox-avatar">{getAvatarLabel(name)}</div>
                  <div className="dm-inbox-body">
                    <div className="dm-inbox-row dm-inbox-row-top">
                      <strong>{name}{isPinned ? ' 📌' : ''}</strong>
                      <span className="dm-inbox-time">{formatTime(conv.last_message_at)}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                      <div className="dm-inbox-preview" style={{ flex: 1 }}>
                        {conv.last_message || '点击进入会话'}
                      </div>
                      {conv.unread_count > 0 && (
                        <span className="dm-inbox-unread">{conv.unread_count}</span>
                      )}
                    </div>
                  </div>
                </button>
                {/* Swipe-style actions */}
                <div className="dm-inbox-actions">
                  <button
                    className={`dm-pin-btn ${isPinned ? 'active' : ''}`}
                    onClick={() => onTogglePinConversation(conv.id)}
                    type="button"
                  >
                    {isPinned ? '📌 已置顶' : '置顶'}
                  </button>
                  <button
                    className="btn btn-sm btn-ghost"
                    onClick={() => onDelete(conv)}
                    type="button"
                    style={{ color: '#FF5A5F', fontSize: '12px' }}
                  >
                    删除
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

/* ── DmChat (full-screen, hides bottom nav) ──────────── */
function DmChat({
  conversation,
  messages,
  input,
  setInput,
  sending,
  agentReply,
  setAgentReply,
  suggestion,
  suggesting,
  commonCommunities,
  onBack,
  onSend,
  onSuggest,
  onStartAgentChat,
  agentChatting,
}) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const partnerName = conversation.partner?.nickname || '未知用户'

  return (
    <div className="dm-chat-shell">
      {/* Header */}
      <div className="dm-chat-header">
        <button className="header-back-btn" onClick={onBack} type="button">
          <BackIcon />
          返回
        </button>
        <div className="dm-chat-avatar">{getAvatarLabel(partnerName)}</div>
        <span className="dm-chat-name">{partnerName}</span>
      </div>

      {/* Community tags */}
      {commonCommunities.length > 0 && (
        <div style={{ padding: '8px 16px', display: 'flex', gap: '6px', flexWrap: 'wrap', borderBottom: '1px solid var(--c-border)', background: 'var(--c-bg)' }}>
          {commonCommunities.map((name) => (
            <span key={name} className="interest-tag" style={{ fontSize: '11px' }}>{name}</span>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="dm-thread">
        {messages.map((msg) => {
          const isPartner = msg.sender_id === conversation.partner?.id
          return (
            <div key={msg.id} className={`dm-message-row ${isPartner ? '' : 'self'}`}>
              {isPartner && (
                <div className="dm-message-avatar">{getAvatarLabel(partnerName)}</div>
              )}
              <div
                className={`chat-bubble ${isPartner ? 'assistant' : 'user'}`}
                style={{ maxWidth: '76%' }}
              >
                {msg.content}
                <div style={{ fontSize: '10px', opacity: 0.6, marginTop: '4px' }}>
                  {formatTime(msg.created_at)}
                </div>
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="dm-chat-input-bar">
        {/* Emoji row */}
        <div className="dm-emoji-row">
          {['🙂', '😂', '👍', '❤️', '🔥', '👏'].map((emoji) => (
            <button
              key={emoji}
              className="dm-emoji-btn"
              onClick={() => setInput((prev) => `${prev}${emoji}`)}
              type="button"
            >
              {emoji}
            </button>
          ))}
        </div>

        {/* Text + send */}
        <div className="dm-input-row">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入私信内容..."
            disabled={sending}
            style={{
              flex: 1,
              padding: '12px 16px',
              minHeight: '44px',
              background: 'var(--c-interactive-bg)',
              border: '1px solid var(--c-border)',
              borderRadius: 'var(--radius-full)',
              color: 'var(--c-text-primary)',
              fontSize: '15px',
              fontFamily: 'inherit',
              outline: 'none',
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                onSend()
              }
            }}
          />
          <button
            className="chat-send-btn"
            onClick={onSend}
            disabled={sending || !input.trim()}
            aria-label="发送"
          >
            <SendIcon />
          </button>
        </div>

        {/* Agent assist row */}
        <div className="dm-assist-row">
          <label className="dm-assist-label">
            <input
              type="checkbox"
              checked={agentReply}
              onChange={(e) => setAgentReply(e.target.checked)}
            />
            让对方 Agent 代聊
          </label>
          <button
            className="btn btn-sm btn-secondary"
            style={{ borderRadius: 'var(--radius-full)' }}
            onClick={onSuggest}
            disabled={suggesting}
          >
            {suggesting ? '生成中...' : '💡 建议'}
          </button>
          {suggestion && (
            <button
              className="btn btn-sm btn-ghost"
              onClick={() => setInput(suggestion)}
            >
              使用
            </button>
          )}
        </div>

        <div style={{ padding: '0 16px', marginBottom: '8px' }}>
          <button
            className="btn btn-sm btn-ghost"
            style={{ width: '100%', color: 'var(--c-accent)', border: '1px solid var(--c-accent)' }}
            onClick={onStartAgentChat}
            disabled={agentChatting}
          >
             {agentChatting ? '🤖 Agent 正在沟通中...' : '🤖 开始 Agent 自动对谈并生成报告'}
          </button>
        </div>

        {suggestion && (
          <div className="dm-suggestion-box">
            建议：{suggestion}
          </div>
        )}
      </div>
    </div>
  )
}

/* ── World (DM Inbox only — no more seg-control) ─────── */
export default function World({ setHideNav, showToast, onUnreadChange, pendingDmTargetId, onDmStarted, isActive }) {
  const [conversations, setConversations] = useState([])
  const [currentConversation, setCurrentConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [commonCommunities, setCommonCommunities] = useState([])
  const [dmInput, setDmInput] = useState('')
  const [dmSending, setDmSending] = useState(false)
  const [agentReply, setAgentReply] = useState(false)
  const [suggestion, setSuggestion] = useState('')
  const [suggesting, setSuggesting] = useState(false)
  const [pinnedConversationIds, setPinnedConversationIds] = useState([])
  const [agentChatting, setAgentChatting] = useState(false)

  // Load pinned from storage
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem('dm_pinned_conversations')
      if (!saved) return
      const parsed = JSON.parse(saved)
      if (Array.isArray(parsed)) {
        setPinnedConversationIds(parsed.filter((id) => typeof id === 'string'))
      }
    } catch (e) {
      console.error('load pinned failed', e)
    }
  }, [])

  useEffect(() => {
    window.localStorage.setItem('dm_pinned_conversations', JSON.stringify(pinnedConversationIds))
  }, [pinnedConversationIds])

  // Tell App whether to hide the bottom nav (when in DM chat)
  useEffect(() => {
    const inChat = currentConversation !== null
    setHideNav?.(inChat)
  }, [currentConversation, setHideNav])

  // Handle pending DM target properly via props
  useEffect(() => {
    if (pendingDmTargetId) {
      handleStartDm(pendingDmTargetId)
      onDmStarted?.()
    }
  }, [pendingDmTargetId])

  const refreshConversations = async (keepCurrent = true) => {
    const data = await listDmConversations()
    const convs = data.conversations || []
    setConversations(convs)
    const total = convs.reduce((a, c) => a + (c.unread_count || 0), 0)
    onUnreadChange?.(total)
    if (keepCurrent && currentConversation) {
      const updated = convs.find((item) => item.id === currentConversation.id)
      if (updated) setCurrentConversation(updated)
    }
  }

  // Refresh conversations when drawer opens so data is never stale
  useEffect(() => {
    if (isActive) {
      refreshConversations(false).catch(console.error)
    }
  }, [isActive])

  const openConversation = async (conv) => {
    setCurrentConversation(conv)
    try {
      const [msgData] = await Promise.all([
        listDmMessages(conv.id),
        markDmRead(conv.id).catch(() => {}),
      ])
      setMessages(msgData.messages || [])
      setSuggestion('')
      setCommonCommunities([])
      refreshConversations().catch(() => {})
    } catch (e) {
      console.error('openConversation error', e)
    }
  }

  const handleStartDm = async (targetUserId, sourceCommunity) => {
    try {
      const data = await startDmConversation(targetUserId, sourceCommunity)
      const newConv = data.conversation
      setCurrentConversation(newConv)
      const [msgData] = await Promise.all([
        listDmMessages(newConv.id),
        refreshConversations(),
      ])
      setMessages(msgData.messages || [])
      setCommonCommunities([])
    } catch (e) {
      console.error('startDm error', e)
    }
  }

  const goBackToInbox = () => {
    setCurrentConversation(null)
    setMessages([])
    setSuggestion('')
    setCommonCommunities([])
    refreshConversations(false).catch(console.error)
  }

  const handleSendDm = async () => {
    const content = dmInput.trim()
    if (!content || !currentConversation || dmSending) return
    setDmSending(true)
    setDmInput('')
    try {
      await sendDmMessage(currentConversation.id, content, agentReply)
      const conv = currentConversation
      const msgData = await listDmMessages(conv.id)
      setMessages(msgData.messages || [])
      refreshConversations().catch(() => {})
      if (agentReply) {
        setTimeout(async () => {
            try {
              const [later] = await Promise.all([
                listDmMessages(conv.id),
                markDmRead(conv.id).catch(() => {}),
              ])
              setMessages(later.messages || [])
              refreshConversations().catch(() => {})
            } catch (_) {}
        }, 3500)
      }
    } finally {
      setDmSending(false)
    }
  }

  const handleSuggest = async () => {
    if (!currentConversation || suggesting) return
    setSuggesting(true)
    try {
      const data = await getDmSuggestion(currentConversation.id)
      setSuggestion(data.suggestion?.text || '')
    } catch (e) {
      console.error('suggest dm error', e)
      setSuggestion('')
    } finally {
      setSuggesting(false)
    }
  }

  const handleStartAgentChat = async () => {
    if (!currentConversation || agentChatting) return
    setAgentChatting(true)
    showToast?.('已启动 Agent 对接，请稍候在屏幕中查看进度或等待报告')
    const convId = currentConversation.id
    try {
      await startAgentChat(convId)
      
      let ticks = 0
      const poll = setInterval(async () => {
        ticks++
          try {
            const [data] = await Promise.all([
              listDmMessages(convId),
              markDmRead(convId).catch(() => {}),
            ])
            // We only update messages if we are still viewing the active conversation
            setMessages(prev => {
                // Because of closure we just use the functional update or ignore if we switched tabs.
                return data.messages || []
            })
            refreshConversations(false).catch(() => {})
          } catch(e) {}
        
        if (ticks >= 20) { // 20 * 3s = 60s
           clearInterval(poll)
           setAgentChatting(false)
           showToast?.('Agent 自动对话可能已结束，请前往 Report 页面查看总结报告')
        }
      }, 3000)
    } catch (e) {
      showToast?.('启动失败: ' + e.message)
      setAgentChatting(false)
    }
  }

  const handleDeleteConversation = async (conv) => {
    await deleteDmConversation(conv.id)
    setPinnedConversationIds((prev) => prev.filter((id) => id !== conv.id))
    if (currentConversation?.id === conv.id) {
      setCurrentConversation(null)
      setMessages([])
      setCommonCommunities([])
    }
    await refreshConversations()
    showToast?.('已删除会话')
  }

  const handleTogglePinConversation = (convId) => {
    setPinnedConversationIds((prev) =>
      prev.includes(convId) ? prev.filter((id) => id !== convId) : [convId, ...prev]
    )
  }

  useEffect(() => {
    listDmConversations()
      .then((data) => {
        const convs = data.conversations || []
        setConversations(convs)
        const total = convs.reduce((a, c) => a + (c.unread_count || 0), 0)
        onUnreadChange?.(total)
      })
      .catch(console.error)
  }, [])

  // If in a DM chat, show full-screen DM (breaks out of drawer via position:fixed AND ReactDOM.createPortal)
  const chatUI = currentConversation ? (
    <div style={{ position: 'fixed', inset: 0, zIndex: 99999, background: 'var(--c-bg)', display: 'flex', flexDirection: 'column' }}>
      <DmChat
        conversation={currentConversation}
        messages={messages}
        input={dmInput}
        setInput={setDmInput}
        sending={dmSending}
        agentReply={agentReply}
        setAgentReply={setAgentReply}
        suggestion={suggestion}
        suggesting={suggesting}
        commonCommunities={commonCommunities}
        onBack={goBackToInbox}
        onSend={handleSendDm}
        onSuggest={handleSuggest}
        onStartAgentChat={handleStartAgentChat}
        agentChatting={agentChatting}
      />
    </div>
  ) : null

  return (
    <>
      {chatUI && createPortal(chatUI, document.body)}
      <DmInbox
        conversations={conversations}
        pinnedConversationIds={pinnedConversationIds}
        onOpenConversation={openConversation}
        onTogglePinConversation={handleTogglePinConversation}
        onDelete={handleDeleteConversation}
      />
    </>
  )
}
