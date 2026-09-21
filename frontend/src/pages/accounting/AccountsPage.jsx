import { useState, useEffect, useCallback } from 'react'
import AccountTree from '../../components/accounting/accounts/AccountTree'
import CreateAccountModal from '../../components/accounting/accounts/CreateAccountModal'
import { accountingService } from '../../services/accountingService'
import { useToast } from '../../components/ui'
import { Alert, Button, ConfirmDialog, PageContainer, PageHeader, Skeleton } from '../../components/ui'
import { space } from '../../lib/tokens'

const skeletonWrapperStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: space[2],
  marginTop: space[2],
}

export default function AccountsPage() {
  const toast = useToast()
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [pendingDeactivate, setPendingDeactivate] = useState(null)
  const [deactivating, setDeactivating] = useState(false)

  const fetchAccounts = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await accountingService.getAccounts({ tree: 'true' })
      setAccounts(data)
    } catch {
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

  function handleDeactivate(account) {
    setPendingDeactivate(account)
  }

  async function confirmDeactivate() {
    const account = pendingDeactivate
    if (!account) return
    setDeactivating(true)
    try {
      await accountingService.deleteAccount(account.id)
      await fetchAccounts()
      toast.success(`Account "${account.name}" deactivated.`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to deactivate account.')
    } finally {
      setDeactivating(false)
      setPendingDeactivate(null)
    }
  }

  return (
    <PageContainer>
      <PageHeader
        title="Chart of Accounts"
        description="Manage your account structure and ledger categories."
        breadcrumbs={[{ label: 'Accounting' }, { label: 'Chart of Accounts' }]}
        primaryAction={
          <Button variant="primary" onClick={handleOpenCreate}>
            Create Account
          </Button>
        }
      />

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <div style={skeletonWrapperStyle} aria-busy="true" aria-live="polite">
          <Skeleton height="44px" />
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} height="40px" />
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

      <ConfirmDialog
        open={Boolean(pendingDeactivate)}
        title="Deactivate account"
        description={
          pendingDeactivate
            ? `Deactivate account "${pendingDeactivate.name}"? This action cannot be undone.`
            : ''
        }
        confirmLabel="Deactivate"
        tone="danger"
        loading={deactivating}
        onConfirm={confirmDeactivate}
        onCancel={() => setPendingDeactivate(null)}
      />
    </PageContainer>
  )
}
