import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import api, { setTokens, setActiveTenant } from '../services/api'

export default function RegisterPage() {
  const [searchParams] = useSearchParams()
  const invitationToken = searchParams.get('token')
  const [form, setForm] = useState({ email: '', password: '', company_name: '' })
  const [error, setError] = useState('')
  const navigate = useNavigate()

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
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
    }
  }

  const isInvited = Boolean(invitationToken)

  return (
    <div>
      <h1>{isInvited ? 'Accept Invitation' : 'Create Your Account'}</h1>
      {isInvited && <p>You have been invited to join a team.</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={handleSubmit}>
        {!isInvited && (
          <div>
            <label>Company Name</label>
            <input name="company_name" value={form.company_name} onChange={handleChange} required />
          </div>
        )}
        <div>
          <label>Email</label>
          <input name="email" type="email" value={form.email} onChange={handleChange} required />
        </div>
        <div>
          <label>Password</label>
          <input name="password" type="password" minLength={8} value={form.password} onChange={handleChange} required />
        </div>
        <button type="submit">{isInvited ? 'Accept & Register' : 'Create Account'}</button>
      </form>
      <p>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </div>
  )
}
