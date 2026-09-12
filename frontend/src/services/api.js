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

async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const csrf = csrfToken()
      const { data } = await axios.post(
        `${api.defaults.baseURL}/auth/refresh/`,
        {},
        { withCredentials: true, headers: csrf ? { 'X-CSRFToken': csrf } : {} },
      )
      localStorage.setItem('accessToken', data.access)
      return data.access
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