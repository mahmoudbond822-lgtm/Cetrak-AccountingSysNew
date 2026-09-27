import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const tenantId = localStorage.getItem('activeTenantId')
  if (tenantId) {
    config.headers['X-Tenant-ID'] = tenantId
  }
  return config
})

export function readCookie(name) {
  const nameEq = `${name}=`
  const parts = document.cookie.split(';')
  for (const part of parts) {
    const trimmed = part.trim()
    if (trimmed.startsWith(nameEq)) {
      return decodeURIComponent(trimmed.slice(nameEq.length))
    }
  }
  return null
}

export function csrfToken() {
  return readCookie('csrftoken')
}

let refreshPromise = null

// A throttled refresh (HTTP 429) is a transient condition, not a dead session.
// Retry it once after the server's own Retry-After hint, capped so a bad value
// can never park the request.
const REFRESH_RETRY_MAX_WAIT_SECONDS = 10

function retryAfterSeconds(error) {
  const header = error.response?.headers?.['retry-after']
  if (!header) return 0
  const seconds = Number.parseInt(header, 10)
  if (!Number.isFinite(seconds) || seconds <= 0) return 0
  return Math.min(seconds, REFRESH_RETRY_MAX_WAIT_SECONDS)
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function requestRefresh() {
  const csrf = csrfToken()
  const { data } = await axios.post(
    `${api.defaults.baseURL}/auth/refresh/`,
    {},
    { withCredentials: true, headers: csrf ? { 'X-CSRFToken': csrf } : {} },
  )
  return data.access
}

async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      let access
      try {
        access = await requestRefresh()
      } catch (error) {
        // Still single-flight: the retry happens inside the same shared promise,
        // so concurrent 401s cannot fan out into several refresh calls.
        const wait = retryAfterSeconds(error)
        if (!wait) throw error
        await sleep(wait * 1000)
        access = await requestRefresh()
      }
      localStorage.setItem('accessToken', access)
      return access
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

function clearSessionAndRedirect(error) {
  localStorage.clear()
  window.location.href = '/login'
  return Promise.reject(error)
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const access = await refreshAccessToken()
        originalRequest.headers.Authorization = `Bearer ${access}`
        return api(originalRequest)
      } catch (refreshError) {
        return clearSessionAndRedirect(refreshError)
      }
    }
    return Promise.reject(error)
  },
)

export function setTokens(access) {
  localStorage.setItem('accessToken', access)
}

export function setActiveTenant(id, name, role) {
  localStorage.setItem('activeTenantId', id)
  localStorage.setItem('activeTenantName', name)
  localStorage.setItem('activeTenantRole', role)
}

export function clearAuth() {
  localStorage.clear()
}

export function getAuth() {
  return {
    accessToken: localStorage.getItem('accessToken'),
    activeTenantId: localStorage.getItem('activeTenantId'),
    activeTenantName: localStorage.getItem('activeTenantName'),
    activeTenantRole: localStorage.getItem('activeTenantRole'),
  }
}

export default api