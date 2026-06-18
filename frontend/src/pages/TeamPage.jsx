import { useState, useEffect } from 'react'
import api, { getAuth } from '../services/api'

export default function TeamPage() {
  const [members, setMembers] = useState([])
  const [invitations, setInvitations] = useState([])
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('Accountant')
  const [error, setError] = useState('')
  const { activeTenantRole } = getAuth()
  const isAdmin = activeTenantRole === 'Admin'

  useEffect(() => {
    if (!isAdmin) return
    api.get('/tenants/members/').then(({ data }) => setMembers(data.results)).catch(() => {})
    api.get('/tenants/invitations/').then(({ data }) => setInvitations(data.results)).catch(() => {})
  }, [isAdmin])

  async function handleInvite(e) {
    e.preventDefault()
    setError('')
    try {
      const { data } = await api.post('/tenants/invitations/', { email: inviteEmail, role: inviteRole })
      setInvitations((prev) => [...prev, data])
      setInviteEmail('')
    } catch (err) {
      const msg = err.response?.data
      if (typeof msg === 'object') {
        setError(Object.values(msg).flat().join(' '))
      } else {
        setError('Failed to send invitation.')
      }
    }
  }

  async function handleRoleChange(userId, newRole) {
    try {
      const { data } = await api.patch(`/tenants/members/${userId}/role/`, { role: newRole })
      setMembers((prev) => prev.map((m) => (m.user_id === userId ? { ...m, role: data.role } : m)))
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to change role.')
    }
  }

  async function handleRemove(userId) {
    try {
      await api.delete(`/tenants/members/${userId}/`)
      setMembers((prev) => prev.filter((m) => m.user_id !== userId))
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to remove member.')
    }
  }

  async function handleCancelInvite(inviteId) {
    try {
      await api.delete(`/tenants/invitations/${inviteId}/`)
      setInvitations((prev) => prev.filter((i) => i.id !== inviteId))
    } catch {
      setError('Failed to cancel invitation.')
    }
  }

  if (!isAdmin) {
    return <p>You do not have permission to manage the team.</p>
  }

  return (
    <div>
      <h1>Team Management</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <section>
        <h2>Invite Member</h2>
        <form onSubmit={handleInvite} style={{ display: 'flex', gap: '0.5rem', alignItems: 'end' }}>
          <div>
            <label>Email</label>
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label>Role</label>
            <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
              <option value="Accountant">Accountant</option>
              <option value="Manager">Manager</option>
            </select>
          </div>
          <button type="submit">Send Invitation</button>
        </form>
      </section>

      <section>
        <h2>Members ({members.length})</h2>
        <table border="1" cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th>Email</th>
              <th>Name</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.user_id}>
                <td>{m.email}</td>
                <td>{m.display_name || '-'}</td>
                <td>
                  <select
                    value={m.role}
                    onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                  >
                    <option value="Admin">Admin</option>
                    <option value="Manager">Manager</option>
                    <option value="Accountant">Accountant</option>
                  </select>
                </td>
                <td>{m.status}</td>
                <td>
                  <button onClick={() => handleRemove(m.user_id)} style={{ color: 'red' }}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {invitations.length > 0 && (
        <section>
          <h2>Pending Invitations ({invitations.length})</h2>
          <table border="1" cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Expires</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invitations.map((inv) => (
                <tr key={inv.id}>
                  <td>{inv.email}</td>
                  <td>{inv.role}</td>
                  <td>{new Date(inv.expires_at).toLocaleDateString()}</td>
                  <td>{inv.status}</td>
                  <td>
                    <button onClick={() => handleCancelInvite(inv.id)} style={{ color: 'red' }}>
                      Cancel
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}
