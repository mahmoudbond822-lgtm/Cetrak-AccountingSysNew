import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import api, { setTokens, setActiveTenant } from '../services/api'
import AuthLayout from '../components/layout/AuthLayout'
import { Alert, Button, Input } from '../components/ui'
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

const subtitleStyle = {
  fontSize: font.size.bodySmall,
  color: 'var(--text-muted)',
  textAlign: 'center',
}

const linkStyle = {
  fontSize: font.size.bodySmall,
  color: 'var(--brand)',
  textDecoration: 'none',
  fontWeight: 500,
}

export default function RegisterPage() {
  const [searchParams] = useSearchParams()
  const invitationToken = searchParams.get('token')
  const [form, setForm] = useState({ email: '', password: '', company_name: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  const isInvited = Boolean(invitationToken)

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    const payload = { ...form }
    if (invitationToken) {
      payload.invitation_token = invitationToken
    }
    try {
      const { data } = await api.post('/auth/register/', payload)
      setTokens(data.access)
      if (data.user) {
        localStorage.setItem('userEmail', data.user.email)
      }
      if (data.active_tenant) {
        setActiveTenant(data.active_tenant.id, data.active_tenant.name, data.active_tenant.role)
      } else {
        setActiveTenant(data.tenant.id, data.tenant.name, 'admin')
      }
      navigate('/', { replace: true })
    } catch (err) {
      const msg = err.response?.data
      if (typeof msg === 'object') {
        setError(Object.values(msg).flat().join(' '))
      } else {
        setError('Registration failed. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      footer={
        <>
          <span>Already have an account?</span>
          <Link to="/login" style={linkStyle}>Sign in</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} style={formStyle} noValidate>
        <h1 style={titleStyle}>{isInvited ? 'Accept invitation' : 'Create your account'}</h1>
        {isInvited && (
          <p style={subtitleStyle}>You have been invited to join a team.</p>
        )}

        {error && (
          <Alert tone="error" dismissible onDismiss={() => setError('')}>
            {error}
          </Alert>
        )}

        {!isInvited && (
          <Input
            label="Company name"
            name="company_name"
            autoComplete="organization"
            placeholder="Acme Inc."
            value={form.company_name}
            onChange={handleChange}
            required
          />
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
          autoComplete="new-password"
          helperText="At least 8 characters."
          placeholder="Create a password"
          minLength={8}
          value={form.password}
          onChange={handleChange}
          required
        />

        <Button type="submit" variant="primary" loading={submitting} style={{ width: '100%' }}>
          {submitting
            ? 'Creating account…'
            : isInvited
              ? 'Accept & register'
              : 'Create account'}
        </Button>
      </form>
    </AuthLayout>
  )
}
