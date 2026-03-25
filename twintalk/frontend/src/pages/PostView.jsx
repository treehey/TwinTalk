import React, { useState } from 'react'
import { getMe } from '../services/api' // if you want to use the actual user profile logic, though we use initial posts and mockup here

/* ── Icons ── */
const CommentIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5">
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
  </svg>
);

const HeartIcon = ({ fill = "none" }) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill={fill} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
  </svg>
);

/* ── Mock Data ── */
const initialPosts = [
  {
    id: 1,
    userName: 'TwinTalk Official',
    userHandle: '@twintalk',
    timeAgo: '2小时前',
    content: "欢迎来到全新上线的社区动态栏目（Post）。在这里，你可以分享你的想法，记录瞬间，与星球上的灵魂共鸣！",
    likes: 45,
    commentsList: [
      { id: 101, userName: '用户A', content: '太棒了，期待已久！', timeAgo: '1小时前' },
      { id: 102, userName: '用户B', content: '前排占座。', timeAgo: '半小时前' }
    ]
  },
  {
    id: 2,
    userName: 'Design System',
    userHandle: '@system',
    timeAgo: '4小时前',
    content: 'Clarity is achieved through subtraction. 清晰往往源自于做减法。去掉不必要的边界、背景，让内容本身闪光。',
    likes: 18,
    commentsList: [
      { id: 201, userName: 'UI爱好者', content: '极简主义赛高！', timeAgo: '2小时前' }
    ]
  },
  {
    id: 3,
    userName: 'Archive',
    userHandle: '@archive',
    timeAgo: '5小时前',
    content: 'Formatting should be invisible. 排版应当是隐形的。',
    likes: 5,
    commentsList: []
  },
];

/* ── CommentSection ── */
const CommentSection = ({ commentsList, onAddComment }) => {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    if (text.trim()) {
      onAddComment(text.trim());
      setText('');
    }
  };

  return (
    <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px dashed var(--c-border)' }}>
      {commentsList && commentsList.length > 0 ? (
        <div style={{ marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {commentsList.map(comment => (
            <div key={comment.id} style={{ fontSize: '14px', color: 'var(--c-text-primary)' }}>
              <span style={{ fontWeight: 600, marginRight: '8px' }}>{comment.userName}:</span>
              <span>{comment.content}</span>
              <div style={{ fontSize: '12px', color: 'var(--c-text-secondary)', marginTop: '2px' }}>{comment.timeAgo}</div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ fontSize: '13px', color: 'var(--c-text-secondary)', marginBottom: '16px' }}>暂无评论，来抢沙发吧~</div>
      )}
      <div style={{ display: 'flex', gap: '8px' }}>
        <input
          type="text"
          className="form-input"
          style={{ minHeight: '36px', padding: '8px 12px', fontSize: '14px', borderRadius: 'var(--radius-full)' }}
          placeholder="写下你的评论..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          className="btn btn-primary btn-sm"
          style={{ borderRadius: 'var(--radius-full)' }}
          onClick={handleSubmit}
          disabled={!text.trim()}
        >
          发送
        </button>
      </div>
    </div>
  );
};

/* ── Helpers ── */
const getEmojiAvatar = (name) => {
  if (!name) return '🤖';
  const emojis = ['👽', '👾', '🚀', '🔮', '🎭', '⚡', '🔥', '🌟', '🧠', '👁️', '🎲', '🧩'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash += name.charCodeAt(i);
  return emojis[hash % emojis.length];
};

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

/* ── PostCard ── */
const PostCard = ({ post, onLike, likedPosts, onAddComment }) => {
  const isLiked = likedPosts.has(post.id);
  const [showComments, setShowComments] = useState(false);

  const commentsCount = post.commentsList ? post.commentsList.length : (post.comments || 0);

  return (
    <article className="post-card">
      <div className="post-card-header">
        <div 
          className="post-avatar" 
          style={{ 
            background: getAvatarGradient(post.userName),
            color: '#111',
            fontSize: '20px',
            border: 'none',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
          }}
        >
          {getEmojiAvatar(post.userName)}
        </div>
        <div className="post-user-info">
          <span className="post-user-name">{post.userName}</span>
          <span className="post-user-meta">{post.userHandle} · {post.timeAgo}</span>
        </div>
      </div>
      <div className="post-content">{post.content}</div>
      <div className="post-actions">
        <button 
          className="post-action-btn" 
          onClick={() => setShowComments(!showComments)} 
          aria-label="Comment"
          style={{ color: showComments ? 'var(--c-accent)' : '' }}
        >
          <CommentIcon />
          <span>{commentsCount}</span>
        </button>
        <button
          className="post-action-btn"
          style={{ color: isLiked ? 'var(--c-accent)' : '' }}
          onClick={() => onLike(post.id, isLiked)}
          aria-label="Like"
        >
          <HeartIcon fill={isLiked ? "currentColor" : "none"} />
          <span>{post.likes + (isLiked ? 1 : 0)}</span>
        </button>
      </div>
      
      {showComments && (
        <CommentSection 
          commentsList={post.commentsList || []} 
          onAddComment={(text) => onAddComment(post.id, text)} 
        />
      )}
    </article>
  );
};

/* ── PostEditor ── */
const PostEditor = ({ onSubmit }) => {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    if (text.trim()) {
      onSubmit(text.trim());
      setText('');
    }
  };

  return (
    <div style={{ padding: '20px', borderBottom: '1px solid var(--c-border)', backgroundColor: 'var(--c-bg)' }}>
      <textarea
        className="form-textarea"
        style={{
          minHeight: '80px',
          borderColor: 'transparent',
          backgroundColor: 'var(--c-interactive-bg)',
          marginBottom: '10px'
        }}
        placeholder="分享你的最新动态..."
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          className="btn btn-primary btn-sm"
          style={{ paddingLeft: '24px', paddingRight: '24px', borderRadius: 'var(--radius-full)' }}
          onClick={handleSubmit}
          disabled={!text.trim()}
        >
          发布
        </button>
      </div>
    </div>
  );
};

/* ── PostView ── */
export default function PostView({ isActive, showToast }) {
  const [posts, setPosts] = useState(initialPosts);
  const [likedPosts, setLikedPosts] = useState(new Set());

  // Wait for it to become active to fetch actual API if needed later.
  
  if (!isActive) return null;

  const handleLike = (postId, isCurrentlyLiked) => {
    setLikedPosts(prev => {
      const next = new Set(prev);
      if (next.has(postId)) {
        next.delete(postId);
      } else {
        next.add(postId);
      }
      return next;
    });
    if (showToast) {
      showToast(isCurrentlyLiked ? '已取消点赞' : '点赞成功');
    }
  };

  const handleNewPost = (content) => {
    const newPost = {
      id: Date.now(),
      userName: '我',
      userHandle: '@me',
      timeAgo: '刚刚',
      content,
      likes: 0,
      commentsList: []
    };
    setPosts(prev => [newPost, ...prev]);
    if (showToast) showToast('发布成功！');
  };

  const handleAddComment = (postId, text) => {
    setPosts(prev => prev.map(post => {
      if (post.id === postId) {
        return {
          ...post,
          commentsList: [
            ...(post.commentsList || []),
            { id: Date.now(), userName: '我', content: text, timeAgo: '刚刚' }
          ]
        };
      }
      return post;
    }));
    if (showToast) showToast('评论成功！');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header specific to Post View if wanted. But App.jsx has a global header. 
          If we want to add an internal sticky header for this page, we do it here. 
          Usually mobile apps differentiate sections. */}
      <div style={{
        padding: '14px 16px',
        borderBottom: '1px solid var(--c-border)',
        background: 'var(--c-bg)',
        display: 'flex',
        alignItems: 'center',
        position: 'sticky',
        top: 0,
        zIndex: 5
      }}>
        <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--c-text-primary)' }}>✨ 社区动态</div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', overscrollBehaviorY: 'contain', backgroundColor: 'var(--c-feed-bg)' }}>
        <PostEditor onSubmit={handleNewPost} />
        
        <div>
          {posts.map(post => (
            <PostCard 
              key={post.id} 
              post={post} 
              onLike={handleLike} 
              likedPosts={likedPosts}
              onAddComment={handleAddComment}
            />
          ))}
        </div>
        
        {/* Adds padding at bottom so navbar doesn't hide last item */}
        <div style={{ height: 'env(safe-area-inset-bottom, 20px) + 60px' }}></div>
      </div>
    </div>
  );
}
