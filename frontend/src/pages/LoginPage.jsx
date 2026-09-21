import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api, { setTokens, setActiveTenant } from '../services/api'
import AuthLayout from '../components/layout/AuthLayout'
import { Alert, Button, Checkbox, Input } from '../components/ui'
import { font, space } from '../lib/tokens'

const formStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: space[5],
}

const titleStyle = {
  fontSize: font.size.pageTitle,
  fontWeight: 600,
  color: 'var(--text)',
  textAlign: 'center',
}

const rowStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: space[3],
  flexWrap: 'wrap',
}

const linkStyle = {
  fontSize: font.size.bodySmall,
  color: 'var(--brand)',
  textDecoration: 'none',
  fontWeight: 500,
}

export default function LoginPage() {
  const [form, setForm] = useState({ email: '', password: '', remember_me: false })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  function handleChange(e) {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
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
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      footer={
        <>
          <span>Don't have an account?</span>
          <Link to="/register" style={linkStyle}>Create one</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} style={formStyle} noValidate>
        <h1 style={titleStyle}>Sign in</h1>

        {error && (
          <Alert tone="error" dismissible onDismiss={() => setError('')}>
            {error}
          </Alert>
        )}

        <Input
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          value={form.email}
          onChange={handleChange}
          required
        />

        <Input
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          placeholder="Enter your password"
          value={form.password}
          onChange={handleChange}
          required
        />

        <div style={rowStyle}>
          <Checkbox
            label="Remember me"
            name="remember_me"
            checked={form.remember_me}
            onChange={handleChange}
          />
        </div>

        <Button type="submit" variant="primary" loading={submitting} style={{ width: '100%' }}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </AuthLayout>
  )
}
