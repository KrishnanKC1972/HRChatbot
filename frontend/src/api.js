const BASE = import.meta.env.BASE_URL.replace(/\/$/, '')

// API routes live at the server root (e.g. /chat), not under the SPA base (/app),
// so strip the SPA base path and derive the API root.
const API_ROOT = BASE.replace(/\/app$/, '')

function url(path) {
  return `${API_ROOT}/${path}`
}

async function request(path, options = {}) {
  const res = await fetch(url(path), {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export function sendChat(query) {
  return request('chat', { method: 'POST', body: JSON.stringify({ query }) })
}

export function fetchMetrics() {
  return request('metrics')
}

export function fetchHistory(limit = 50) {
  return request(`history?limit=${limit}`)
}

export function runBatchEval(questions) {
  return request('evaluate/batch', {
    method: 'POST',
    body: JSON.stringify(questions && questions.length ? { questions } : {}),
  })
}

export function clearHistory() {
  return request('history', { method: 'DELETE' })
}

export function fetchUnanswered(limit = 100) {
  return request(`unanswered?limit=${limit}`)
}

export function updateUnanswered(id, status) {
  return request(`unanswered/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

export function deleteUnanswered(id) {
  return request(`unanswered/${id}`, { method: 'DELETE' })
}

export function clearUnanswered() {
  return request('unanswered', { method: 'DELETE' })
}
