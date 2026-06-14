import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
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

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const refresh = localStorage.getItem('refreshToken')
      if (refresh) {
        try {
          const { data } = await axios.post(
            `${api.defaults.baseURL}/auth/refresh/`,
            { refresh }
          )
          localStorage.setItem('accessToken', data.access)
          originalRequest.headers.Authorization = `Bearer ${data.access}`
          return api(originalRequest)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      } else {
        localStorage.clear()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export function setTokens(access, refresh) {
  localStorage.setItem('accessToken', access)
  if (refresh) localStorage.setItem('refreshToken', refresh)
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
    refreshToken: localStorage.getItem('refreshToken'),
    activeTenantId: localStorage.getItem('activeTenantId'),
    activeTenantName: localStorage.getItem('activeTenantName'),
    activeTenantRole: localStorage.getItem('activeTenantRole'),
  }
}

export default api
