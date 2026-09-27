import { useState, useEffect } from 'react'
import api, { getAuth } from '../services/api'
import {
  Alert, Badge, Button, Card, CardBody, ConfirmDialog, EmptyState, Input, PageContainer, PageHeader, Pagination, Select,
} from '../components/ui'
import { useToast } from '../components/ui'
import { font, space } from '../lib/tokens'
import { PAGE_SIZE } from '../lib/pagination'

const formStyle = {
  display: 'flex',
  gap: space[3],
  alignItems: 'flex-end',
  flexWrap: 'wrap',
}

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: font.size.bodySmall,
}

const thStyle = {
  textAlign: 'left',
  padding: `${space[3]} ${space[4]}`,
  borderBottom: `1px solid var(--border)`,
  fontWeight: 600,
  color: 'var(--text-muted)',
  background: 'var(--bg-hover)',
  fontSize: font.size.caption,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

const tdStyle = {
  padding: `${space[3]} ${space[4]}`,
  borderBottom: '1px solid var(--border-subtle)',
  color: 'var(--text)',
}

const actionsStyle = {
  ...tdStyle,
  display: 'flex',
  gap: space[1],
}

const statusTone = { Active: 'success', Disabled: 'neutral', Pending: 'warning', Expired: 'neutral', Cancelled: 'neutral' }

export default function TeamPage() {
  const toast = useToast()
  const [members, setMembers] = useState([])
  const [invitations, setInvitations] = useState([])
  const [memberPage, setMemberPage] = useState(1)
  const [memberTotal, setMemberTotal] = useState(0)
  const [inviteTotal, setInviteTotal] = useState(0)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('Accountant')
  const [error, setError] = useState('')
  const [confirm, setConfirm] = useState(null)
  const [busy, setBusy] = useState(false)
  const { activeTenantRole } = getAuth()
  const isAdmin = activeTenantRole === 'Admin'

  useEffect(() => {
    if (!isAdmin) return
    api.get('/tenants/members/', { params: { page: memberPage } })
      .then(({ data }) => {
        if ((data.results || []).length === 0 && memberPage > 1) {
          return api.get('/tenants/members/', { params: { page: 1 } }).then((first) => {
            setMembers(first.data.results || [])
            setMemberTotal(first.data.count ?? 0)
            setMemberPage(1)
          })
        }
        setMembers(data.results)
        setMemberTotal(data.count ?? 0)
      })
      .catch(() => {})
    api.get('/tenants/invitations/', { params: { page_size: 100 } })
      .then(({ data }) => {
        setInvitations(data.results)
        setInviteTotal(data.count ?? 0)
      })
      .catch(() => {})
  }, [isAdmin, memberPage])

  async function handleInvite(e) {
    e.preventDefault()
    setError('')
    try {
      const { data } = await api.post('/tenants/invitations/', { email: inviteEmail, role: inviteRole })
      setInvitations((prev) => [...prev, data])
      setInviteEmail('')
      toast.success(`Invitation sent to ${inviteEmail || 'the invited email'}.`)
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

  function requestToggleStatus(m) {
    const next = m.status === 'Disabled' ? 'Active' : 'Disabled'
    const action = next === 'Disabled' ? 'disable' : 'enable'
    setConfirm({
      title: `${action === 'disable' ? 'Disable' : 'Enable'} member`,
      description: `Are you sure you want to ${action} ${m.email}?`,
      confirmLabel: action === 'disable' ? 'Disable' : 'Enable',
      tone: action === 'disable' ? 'danger' : 'default',
      action: async () => {
        setBusy(true)
        try {
          const { data } = await api.patch(`/tenants/members/${m.user_id}/status/`, { status: next })
          setMembers((prev) =>
            prev.map((x) => (x.user_id === m.user_id ? { ...x, status: data.status } : x)),
          )
        } catch (err) {
          setError(err.response?.data?.detail || `Failed to ${action} member.`)
        } finally {
          setBusy(false)
          setConfirm(null)
        }
      },
    })
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
    return (
      <PageContainer>
        <PageHeader title="Team Management" />
        <Card>
          <CardBody>
            <p style={{ fontSize: font.size.bodySmall, color: 'var(--text-muted)' }}>
              You do not have permission to manage the team.
            </p>
          </CardBody>
        </Card>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Team Management"
        description="Invite members, manage roles and control access."
        breadcrumbs={[{ label: 'Management' }, { label: 'Team' }]}
      />

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      <Card style={{ marginBottom: space[6] }}>
        <CardBody>
          <h2 style={{ fontSize: font.size.cardTitle, fontWeight: 600, marginBottom: space[4] }}>
            Invite member
          </h2>
          <form onSubmit={handleInvite} style={formStyle}>
            <div style={{ flex: '1 1 240px' }}>
              <Input
                label="Email"
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@company.com"
                required
              />
            </div>
            <div style={{ width: '160px' }}>
              <Select
                label="Role"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
              >
                <option value="Accountant">Accountant</option>
                <option value="Manager">Manager</option>
              </Select>
            </div>
            <Button type="submit" variant="primary">Send Invitation</Button>
          </form>
        </CardBody>
      </Card>

      <Card style={{ marginBottom: space[6] }}>
        <CardBody>
          <h2 style={{ fontSize: font.size.cardTitle, fontWeight: 600, marginBottom: space[3] }}>
            Members ({memberTotal})
          </h2>
          {members.length === 0 ? (
            <EmptyState
              title="No members yet"
              description="Invite a colleague to join your team."
            />
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Email</th>
                    <th style={thStyle}>Name</th>
                    <th style={thStyle}>Role</th>
                    <th style={thStyle}>Status</th>
                    <th style={thStyle}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((m) => (
                    <tr key={m.user_id}>
                      <td style={tdStyle}>{m.email}</td>
                      <td style={tdStyle}>{m.display_name || '—'}</td>
                      <td style={tdStyle}>
                        <Select
                          value={m.role}
                          onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                          aria-label={`Change role for ${m.email}`}
                        >
                          <option value="Admin">Admin</option>
                          <option value="Manager">Manager</option>
                          <option value="Accountant">Accountant</option>
                        </Select>
                      </td>
                      <td style={tdStyle}>
                        <Badge tone={statusTone[m.status] || 'neutral'} size="sm" dot>
                          {m.status}
                        </Badge>
                      </td>
                      <td style={actionsStyle}>
                        <Button variant="ghost" size="sm" onClick={() => requestToggleStatus(m)}>
                          {m.status === 'Disabled' ? 'Enable' : 'Disable'}
                        </Button>
                        <Button variant="dangerSoft" size="sm" onClick={() => handleRemove(m.user_id)}>
                          Remove
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Pagination
            page={memberPage}
            pageSize={PAGE_SIZE}
            total={memberTotal}
            onPageChange={setMemberPage}
            style={{ marginTop: space[3], justifyContent: 'flex-start' }}
          />
        </CardBody>
      </Card>

      {invitations.length > 0 && (
        <Card>
          <CardBody>
            <h2 style={{ fontSize: font.size.cardTitle, fontWeight: 600, marginBottom: space[3] }}>
              Pending invitations ({inviteTotal})
            </h2>
            <div style={{ overflowX: 'auto' }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Email</th>
                    <th style={thStyle}>Role</th>
                    <th style={thStyle}>Expires</th>
                    <th style={thStyle}>Status</th>
                    <th style={thStyle}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {invitations.map((inv) => (
                    <tr key={inv.id}>
                      <td style={tdStyle}>{inv.email}</td>
                      <td style={tdStyle}>{inv.role}</td>
                      <td style={tdStyle}>{new Date(inv.expires_at).toLocaleDateString()}</td>
                      <td style={tdStyle}>
                        <Badge tone={statusTone[inv.status] || 'neutral'} size="sm" dot>
                          {inv.status}
                        </Badge>
                      </td>
                      <td style={tdStyle}>
                        <Button variant="dangerSoft" size="sm" onClick={() => handleCancelInvite(inv.id)}>
                          Cancel
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      )}

      <ConfirmDialog
        open={Boolean(confirm)}
        title={confirm?.title}
        description={confirm?.description}
        confirmLabel={confirm?.confirmLabel}
        tone={confirm?.tone}
        loading={busy}
        onConfirm={confirm?.action}
        onCancel={() => setConfirm(null)}
      />
    </PageContainer>
  )
}
