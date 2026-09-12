import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api, { setTokens, setActiveTenant } from '../services/api'

export default function LoginPage() {
  const [form, setForm] = useState({ email: '', password: '', remember_me: false })
  const [error, setError] = useState('')
  const navigate = useNavigate()

  function handleChange(e) {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    try {
      const { data } = await api.post('/auth/login/', form)
      setTokens(data.access)
      if (data.user) {
        localStorage.setItem('userEmail', data.user.email)
      }
      if (data.tenants) {
        localStorage.setItem('tenants', JSON.stringify(data.tenants))
      }
      if (data.active_tenant) {
        setActiveTenant(data.active_tenant.id, data.active_tenant.name, data.active_tenant.role)
        navigate('/', { replace: true })
      } else {
        navigate('/tenant-select', { replace: true })
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.')
    }
  }

  return (
    <div>
      <h1>Sign In</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={handleSubmit}>
        <div>
          <label>Email</label>
          <input name="email" type="email" value={form.email} onChange={handleChange} required />
        </div>
        <div>
          <label>Password</label>
          <input name="password" type="password" value={form.password} onChange={handleChange} required />
        </div>
        <div>
          <label>
            <input name="remember_me" type="checkbox" checked={form.remember_me} onChange={handleChange} />
            Remember me
          </label>
        </div>
        <button type="submit">Sign In</button>
      </form>
      <p>
        Don't have an account? <Link to="/register">Create one</Link>
      </p>
    </div>
  )
}
