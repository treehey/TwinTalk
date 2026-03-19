import React, { useState } from 'react';

const GlobalStyle = () => (
  <style>
    {`
      * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        -webkit-tap-highlight-color: transparent;
      }
      body {
        background-color: #FFFFFF;
        overscroll-behavior-y: none;
      }
      .action-item:active, .nav-item:active {
        color: #D4B84A !important;
      }
      .icon-btn:active {
        opacity: 0.5;
      }
    `}
  </style>
);

const styles = {
  root: {
    '--c-bg': '#FFFFFF',
    '--c-card-start': '#FFFEF0',
    '--c-card-end': '#FFFFFF',
    '--c-text-primary': '#3D3528',
    '--c-text-secondary': '#7A7568',
    '--c-border': '#F0EFE8',
    '--c-interactive-bg': '#FFFBE6',
    '--c-accent': '#D4B84A',
  },
  app: {
    display: 'flex',
    flexDirection: 'column',
    height: '100dvh',
    width: '100vw',
    overflow: 'hidden',
    backgroundColor: '#FFFFFF',
    color: '#3D3528',
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    fontSize: '16px',
    lineHeight: '1.5',
    WebkitFontSmoothing: 'antialiased',
    overscrollBehaviorY: 'none',
  },
  header: {
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid #F0EFE8',
    backgroundColor: '#FFFFFF',
    zIndex: 10,
  },
  headerTitle: {
    color: '#D4B84A',
    fontSize: '20px',
    fontWeight: 400,
    letterSpacing: '0.02em',
    fontFamily: '"Times New Roman", Times, serif',
  },
  iconBtn: {
    background: 'none',
    border: 'none',
    color: '#D4B84A',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '4px',
    margin: '-4px',
    cursor: 'pointer',
  },
  feed: {
    flexGrow: 1,
    overflowY: 'auto',
    overscrollBehaviorY: 'contain',
  },
  post: {
    padding: '24px 20px',
    borderBottom: '1px solid #F0EFE8',
    background: 'linear-gradient(180deg, #FFFEF0 0%, #FFFFFF 100%)',
  },
  postHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '12px',
  },
  avatar: {
    width: '36px',
    height: '36px',
    backgroundColor: '#FFFBE6',
    border: '1px solid #F0EFE8',
    borderRadius: '4px',
    objectFit: 'cover',
    flexShrink: 0,
  },
  userInfo: {
    display: 'flex',
    flexDirection: 'column',
  },
  userName: {
    color: '#3D3528',
    fontSize: '15px',
    fontWeight: 600,
    lineHeight: '1.2',
  },
  userMeta: {
    fontSize: '13px',
    color: '#7A7568',
    marginTop: '2px',
  },
  postContent: {
    color: '#3D3528',
    fontSize: '16px',
    lineHeight: '1.5',
    letterSpacing: '-0.01em',
    marginBottom: '20px',
    wordWrap: 'break-word',
  },
  postActions: {
    display: 'flex',
    gap: '24px',
  },
  actionItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    color: '#7A7568',
    fontSize: '14px',
    background: 'none',
    border: 'none',
    padding: '4px 0',
    cursor: 'pointer',
  },
  actionItemActive: {
    color: '#D4B84A',
  },
  bottomNav: {
    flexShrink: 0,
    display: 'flex',
    justifyContent: 'space-around',
    padding: '12px 0 calc(12px + env(safe-area-inset-bottom))',
    borderTop: '1px solid #F0EFE8',
    backgroundColor: '#FFFFFF',
  },
  navItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#7A7568',
    background: 'none',
    border: 'none',
    padding: '8px 24px',
    cursor: 'pointer',
  },
  navItemActive: {
    color: '#D4B84A',
  },
};

const initialPosts = [
  {
    id: 1,
    userName: 'Editor',
    userHandle: '@editor',
    timeAgo: '2h',
    content: "Sometimes you want to say things, and you're missing an idea to make them with, and missing a word to make the idea with. In the beginning was the word. That's how somebody tried to explain it once. Until something is named, it doesn't exist.",
    comments: 12,
    likes: 45,
  },
  {
    id: 2,
    userName: 'Design System',
    userHandle: '@system',
    timeAgo: '4h',
    content: 'Clarity is achieved through subtraction. The removal of unnecessary borders, backgrounds, and varying corner radii allows the content to surface without interference.',
    comments: 4,
    likes: 18,
  },
  {
    id: 3,
    userName: 'Archive',
    userHandle: '@archive',
    timeAgo: '5h',
    content: 'Formatting should be invisible.',
    comments: 0,
    likes: 5,
  },
];

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

const ShareIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5">
    <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
    <polyline points="16 6 12 2 8 6" />
    <line x1="12" y1="2" x2="12" y2="15" />
  </svg>
);

const Post = ({ post, onLike, likedPosts }) => {
  const isLiked = likedPosts.has(post.id);

  return (
    <article style={styles.post}>
      <div style={styles.postHeader}>
        <div style={styles.avatar} />
        <div style={styles.userInfo}>
          <span style={styles.userName}>{post.userName}</span>
          <span style={styles.userMeta}>{post.userHandle} · {post.timeAgo}</span>
        </div>
      </div>
      <div style={styles.postContent}>{post.content}</div>
      <div style={styles.postActions}>
        <button className="action-item" style={styles.actionItem} aria-label="Comment">
          <CommentIcon />
          {post.comments}
        </button>
        <button
          className="action-item"
          style={{ ...styles.actionItem, ...(isLiked ? styles.actionItemActive : {}) }}
          onClick={() => onLike(post.id)}
          aria-label="Like"
        >
          <HeartIcon fill={isLiked ? "currentColor" : "none"} />
          {post.likes + (isLiked ? 1 : 0)}
        </button>
        <button className="action-item" style={styles.actionItem} aria-label="Share">
          <ShareIcon />
        </button>
      </div>
    </article>
  );
};

const ComposeModal = ({ isOpen, onClose, onSubmit }) => {
  const [text, setText] = useState('');

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (text.trim()) {
      onSubmit(text.trim());
      setText('');
      onClose();
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.3)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'flex-end',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          backgroundColor: '#FFFFFF',
          borderTop: '1px solid #F0EFE8',
          padding: '24px 20px',
          borderRadius: '16px 16px 0 0',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <span style={{ ...styles.headerTitle, fontSize: '16px' }}>New Post</span>
          <button className="icon-btn" style={styles.iconBtn} onClick={onClose} aria-label="Close">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <textarea
          style={{
            width: '100%',
            minHeight: '120px',
            border: '1px solid #F0EFE8',
            borderRadius: '4px',
            padding: '12px',
            fontSize: '16px',
            fontFamily: 'inherit',
            color: '#3D3528',
            backgroundColor: '#FFFEF0',
            resize: 'none',
            outline: 'none',
            lineHeight: '1.5',
          }}
          placeholder="What's on your mind?"
          value={text}
          onChange={e => setText(e.target.value)}
          autoFocus
        />
        <button
          className="icon-btn"
          style={{
            marginTop: '12px',
            width: '100%',
            padding: '12px',
            backgroundColor: '#D4B84A',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: '4px',
            fontSize: '15px',
            fontWeight: 600,
            cursor: 'pointer',
            opacity: text.trim() ? 1 : 0.5,
          }}
          onClick={handleSubmit}
          disabled={!text.trim()}
        >
          Post
        </button>
      </div>
    </div>
  );
};

const App = () => {
  const [activeNav, setActiveNav] = useState('home');
  const [posts, setPosts] = useState(initialPosts);
  const [likedPosts, setLikedPosts] = useState(new Set());
  const [composeOpen, setComposeOpen] = useState(false);

  const handleLike = (postId) => {
    setLikedPosts(prev => {
      const next = new Set(prev);
      if (next.has(postId)) {
        next.delete(postId);
      } else {
        next.add(postId);
      }
      return next;
    });
  };

  const handleNewPost = (content) => {
    const newPost = {
      id: Date.now(),
      userName: 'You',
      userHandle: '@you',
      timeAgo: 'now',
      content,
      comments: 0,
      likes: 0,
    };
    setPosts(prev => [newPost, ...prev]);
  };

  return (
    <div style={styles.app}>
      <GlobalStyle />
      <header style={styles.header}>
        <div style={styles.headerTitle}>Social</div>
        <button
          className="icon-btn"
          style={styles.iconBtn}
          aria-label="Compose new post"
          onClick={() => setComposeOpen(true)}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </header>

      <main style={styles.feed}>
        {posts.map(post => (
          <Post key={post.id} post={post} onLike={handleLike} likedPosts={likedPosts} />
        ))}
      </main>

      <nav style={styles.bottomNav}>
        <button
          className="nav-item"
          style={{ ...styles.navItem, ...(activeNav === 'home' ? styles.navItemActive : {}) }}
          aria-label="Home"
          onClick={() => setActiveNav('home')}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={activeNav === 'home' ? '2.2' : '1.5'} strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'stroke-width 0.2s' }}>
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
          </svg>
        </button>
        <button
          className="nav-item"
          style={{ ...styles.navItem, ...(activeNav === 'search' ? styles.navItemActive : {}) }}
          aria-label="Search"
          onClick={() => setActiveNav('search')}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={activeNav === 'search' ? '2.2' : '1.5'} strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'stroke-width 0.2s' }}>
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </button>
        <button
          className="nav-item"
          style={{ ...styles.navItem, ...(activeNav === 'notifications' ? styles.navItemActive : {}) }}
          aria-label="Notifications"
          onClick={() => setActiveNav('notifications')}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={activeNav === 'notifications' ? '2.2' : '1.5'} strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'stroke-width 0.2s' }}>
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        </button>
        <button
          className="nav-item"
          style={{ ...styles.navItem, ...(activeNav === 'profile' ? styles.navItemActive : {}) }}
          aria-label="Profile"
          onClick={() => setActiveNav('profile')}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={activeNav === 'profile' ? '2.2' : '1.5'} strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'stroke-width 0.2s' }}>
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </button>
      </nav>

      <ComposeModal
        isOpen={composeOpen}
        onClose={() => setComposeOpen(false)}
        onSubmit={handleNewPost}
      />
    </div>
  );
};

export default App;