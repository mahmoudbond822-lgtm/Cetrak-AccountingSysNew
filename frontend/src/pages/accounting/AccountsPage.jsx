import { useState, useEffect, useCallback } from 'react'
import AccountingNav from '../../components/Layout/AccountingNav'
import AccountTree from '../../components/accounting/accounts/AccountTree'
import CreateAccountModal from '../../components/accounting/accounts/CreateAccountModal'
import { accountingService } from '../../services/accountingService'

const pageStyle = { maxWidth: '960px', margin: '0 auto', padding: '1.5rem' }
const headerStyle = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600 }
const btnPrimary = {
  cursor: 'pointer', background: 'var(--accent)', color: '#fff',
  border: 'none', borderRadius: '6px', padding: '0.5rem 1rem',
  fontSize: '0.875rem', fontWeight: 500,
}
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)

  const fetchAccounts = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await accountingService.getAccounts({ tree: 'true' })
      setAccounts(data)
    } catch (err) {
      setError('Failed to load accounts. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAccounts() }, [fetchAccounts])

  function handleOpenCreate() {
    setEditing(null)
    setShowModal(true)
  }

  function handleEdit(account) {
    setEditing(account)
    setShowModal(true)
  }

  async function handleDeactivate(account) {
    if (!window.confirm(`Deactivate account "${account.name}"? This action cannot be undone.`)) return
    try {
      await accountingService.deleteAccount(account.id)
      fetchAccounts()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to deactivate account.'
      alert(msg)
    }
  }

  return (
    <div>
      <AccountingNav />
      <div style={pageStyle}>
        <div style={headerStyle}>
          <h1 style={titleStyle}>Chart of Accounts</h1>
          <button style={btnPrimary} onClick={handleOpenCreate}>
            Create Account
          </button>
        </div>

        {error && (
          <div style={{ padding: '0.75rem 1rem', background: '#FFF3F3', border: '1px solid #F44336', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        {loading ? (
          <div>
            {[...Array(5)].map((_, i) => (
              <div key={i} style={skeletonStyle} />
            ))}
          </div>
        ) : (
          <AccountTree
            accounts={accounts}
            onEdit={handleEdit}
            onDeactivate={handleDeactivate}
          />
        )}

        <CreateAccountModal
          open={showModal}
          onClose={() => setShowModal(false)}
          account={editing}
          accounts={accounts}
          onSaved={fetchAccounts}
        />
      </div>
    </div>
  )
}
