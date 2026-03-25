/** API service — communicates with Flask backend */

const HOST = '';
const API_BASE = `${HOST}/api`;

function getUserId() {
  return localStorage.getItem('dt_user_id');
}

function setUserId(id) {
  localStorage.setItem('dt_user_id', id);
}

async function request(path, options = {}) {
  const userId = getUserId();
  const headers = {
    'Content-Type': 'application/json',
    ...(userId && { 'X-User-Id': userId }),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  // Some failures (proxy/downstream/network gateway) can return an empty body.
  const raw = await res.text();
  let data = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    const message =
      (data && (data.error || data.description || data.message)) ||
      raw ||
      `请求失败 (${res.status})`;
    throw new Error(message);
  }

  if (data !== null) {
    return data;
  }
  return { success: true };
}

// ---- Auth ----
export async function register(phone_number, password) {
  const data = await request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ phone_number, password }),
  });
  if (data?.user?.id) {
    setUserId(data.user.id);
  }
  return data;
}


export async function login(phone_number, password) {
  const data = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ phone_number, password }),
  });
  if (data?.user?.id) {
    setUserId(data.user.id);
  }
  return data;
}


export async function getMe() {
  return request('/auth/me');
}

export async function completeOnboarding() {
  return request('/auth/complete-onboarding', { method: 'POST' });
}

export function isLoggedIn() {
  return !!getUserId();
}

export function logout() {
  localStorage.removeItem('dt_user_id');
}

// ---- Questionnaires ----
export async function listQuestionnaires() {
  return request('/questionnaires');
}

export async function getQuestionnaire(id) {
  return request(`/questionnaires/${id}`);
}

export async function submitAnswers(questionnaireId, answers) {
  return request(`/questionnaires/${questionnaireId}/submit`, {
    method: 'POST',
    body: JSON.stringify({ answers }),
  });
}

export async function getOnboardingQuestionnaire() {
  const data = await listQuestionnaires();
  const qs = data.questionnaires || [];
  return qs.find((q) => q.category === 'onboarding') || null;
}

// ---- Profile ----
export async function buildProfile() {
  return request('/profiles/build', { method: 'POST' });
}

export async function getMyProfile() {
  return request('/profiles/me');
}

export async function getMyShades() {
  return request('/profiles/me/shades');
}

// ---- Alignment ----
export async function getAlignmentQuestions() {
  return request('/profiles/alignment/questions');
}

export async function submitAlignmentAnswers(answers) {
  return request('/profiles/alignment/submit', {
    method: 'POST',
    body: JSON.stringify({ answers }),
  });
}

// ---- Chat ----
export async function sendMessage(message, sessionId, shade) {
  return request('/chat/message', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId, shade }),
  });
}

export async function getChatSessions() {
  return request('/chat/sessions');
}

export async function getSessionMessages(sessionId) {
  return request(`/chat/sessions/${sessionId}/messages`);
}

// ---- Memories ----
export async function listMemories() {
  return request('/memories/');
}

export async function addMemory(content) {
  return request('/memories/', {
    method: 'POST',
    body: JSON.stringify({ content, memory_type: 'user_added' }),
  });
}

export async function deleteMemory(memoryId) {
  return request(`/memories/${memoryId}`, { method: 'DELETE' });
}

export async function editMemory(memoryId, updates) {
  return request(`/memories/${memoryId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export async function searchMemories(query) {
  const q = encodeURIComponent(query || '')
  return request(`/memories/?search=${q}`);
}

// ---- Social ----
export async function followUser(userId) {
  return request(`/social/follow/${userId}`, { method: 'POST' });
}

export async function unfollowUser(userId) {
  return request(`/social/unfollow/${userId}`, { method: 'POST' });
}

export async function findMatches(limit = 10, refreshToken = '') {
  const token = encodeURIComponent(refreshToken || '')
  return request(`/social/match?limit=${limit}&refresh_token=${token}`);
}

export async function getFollowing() {
  return request('/social/following');
}

export async function getMyProfileMemories() {
  return request('/profiles/me');
}

// ---- Direct Messages ----
export async function listDmConversations() {
  return request('/social/dm/conversations')
}

export async function startDmConversation(targetUserId, sourceCommunity = '') {
  return request('/social/dm/conversations/start', {
    method: 'POST',
    body: JSON.stringify({ target_user_id: targetUserId, source_community: sourceCommunity }),
  })
}

export async function listDmMessages(conversationId) {
  return request(`/social/dm/conversations/${conversationId}/messages`)
}

export async function sendDmMessage(conversationId, message, agentReply = false) {
  return request(`/social/dm/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ message, content_type: 'text', agent_reply: agentReply }),
  })
}

export async function getDmSuggestion(conversationId) {
  return request(`/social/dm/conversations/${conversationId}/suggestion`, {
    method: 'POST',
  })
}

export async function markDmRead(conversationId) {
  return request(`/social/dm/conversations/${conversationId}/read`, {
    method: 'POST',
  })
}

export async function deleteDmConversation(conversationId) {
  return request(`/social/dm/conversations/${conversationId}`, {
    method: 'DELETE',
  })
}

export async function getDmStats() {
  return request('/social/dm/stats')
}

export async function syncDmMemory() {
  return request('/social/dm/sync-memory', {
    method: 'POST',
  })
}

// ---- Agent Chat & Reports ----
export async function startAgentChat(conversationId) {
  return request(`/social/dm/conversations/${conversationId}/agent-chat`, {
    method: 'POST',
  })
}

export async function getAgentReports() {
  return request('/reports/')
}

export async function getAgentReport(reportId) {
  return request(`/reports/${reportId}`)
}

export async function deleteAgentReport(reportId) {
  return request(`/reports/${reportId}`, {
    method: 'DELETE',
  })
}

export async function getMirrorGreeting(sessionId) {
  return request('/chat/mirror_greeting', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId })
  })
}
