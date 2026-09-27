import { useState, useEffect, useCallback, useRef } from 'react'
import CustomerModal from '../../components/sales/customers/CustomerModal'
import { getAuth } from '../../services/api'
import { salesService } from '../../services/salesService'
import { useToast } from '../../components/ui'
import {
  Alert, Badge, Button, ConfirmDialog, PageContainer, PageHeader, Pagination, Table,
} from '../../components/ui'
import { space } from '../../lib/tokens'
import { PAGE_SIZE } from '../../lib/pagination'

function nextCustomerCode(customers) {
  const used = new Set()
  for (const c of customers || []) {
    const m = /^CUS-(\d+)$/.exec(c.code || '')
    if (m) used.add(parseInt(m[1], 10))
  }
  let n = 1
  while (used.has(n)) n += 1
  return `CUS-${String(n).padStart(4, '0')}`
}

export default function CustomersPage() {
  const toast = useToast()
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [notice, setNotice] = useState('')
  const [pendingDeactivate, setPendingDeactivate] = useState(null)
  const [deactivating, setDeactivating] = useState(false)
  const previewRef = useRef('')

  const fetchCustomers = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await salesService.getCustomers({ page })
      if ((data.results || []).length === 0 && page > 1) {
        const first = await salesService.getCustomers({ page: 1 })
        setCustomers(first.data.results || [])
        setTotal(first.data.count ?? 0)
        setPage(1)
      } else {
        setCustomers(data.results || [])
        setTotal(data.count ?? 0)
      }
    } catch {
      setError('Failed to load customers. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { fetchCustomers() }, [fetchCustomers])

  function handleOpenCreate() {
    previewRef.current = nextCustomerCode(customers)
    setNotice('')
    setEditing(null)
    setShowModal(true)
  }

  async function handleSaved(saved) {
    await fetchCustomers()
    if (saved?.code && saved.code !== previewRef.current) {
      setNotice(`Saved with auto-assigned code ${saved.code} (preview was ${previewRef.current}).`)
    }
  }

  function handleEdit(customer) {
    setEditing(customer)
    setShowModal(true)
  }

  function handleDeactivate(customer) {
    setPendingDeactivate(customer)
  }

  async function confirmDeactivate() {
    const customer = pendingDeactivate
    if (!customer) return
    setDeactivating(true)
    try {
      await salesService.deleteCustomer(customer.id)
      await fetchCustomers()
      toast.success(`Customer "${customer.name}" deactivated.`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to deactivate customer.')
    } finally {
      setDeactivating(false)
      setPendingDeactivate(null)
    }
  }

  const columns = [
    { key: 'code', label: 'Code' },
    { key: 'name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'phone', label: 'Phone' },
    { key: 'tax_id', label: 'Tax ID' },
    {
      key: 'is_active',
      label: 'Status',
      render: (c) => (
        <Badge tone={c.is_active ? 'success' : 'neutral'} size="sm" dot>
          {c.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    ...(canManage ? [{
      key: 'actions',
      label: 'Actions',
      isActions: true,
      render: (c) => (
        <div style={{ display: 'flex', gap: space[1], justifyContent: 'flex-end' }}>
          <Button variant="ghost" size="sm" onClick={() => handleEdit(c)}>Edit</Button>
          {c.is_active && (
            <Button variant="dangerSoft" size="sm" onClick={() => handleDeactivate(c)}>
              Deactivate
            </Button>
          )}
        </div>
      ),
    }] : []),
  ]

  return (
    <PageContainer>
      <PageHeader
        title="Customers"
        description="Manage your customer directory and contact details."
        breadcrumbs={[{ label: 'Sales' }, { label: 'Customers' }]}
        primaryAction={
          canManage ? (
            <Button variant="primary" onClick={handleOpenCreate}>Create Customer</Button>
          ) : undefined
        }
      />

      {notice && (
        <Alert tone="success" dismissible onDismiss={() => setNotice('')} style={{ marginBottom: space[4] }}>
          {notice}
        </Alert>
      )}

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      <Table
        columns={columns}
        data={customers}
        loading={loading}
        emptyTitle="No customers yet"
        emptyDescription="Create your first customer to start issuing invoices."
        emptyAction={canManage ? <Button variant="primary" onClick={handleOpenCreate}>Create Customer</Button> : undefined}
      />

      <Pagination
        page={page}
        pageSize={PAGE_SIZE}
        total={total}
        onPageChange={setPage}
        style={{ marginTop: space[3], justifyContent: 'flex-start' }}
      />

      <CustomerModal
        open={showModal}
        onClose={() => setShowModal(false)}
        customer={editing}
        nextCode={nextCustomerCode(customers)}
        onSaved={handleSaved}
      />

      <ConfirmDialog
        open={Boolean(pendingDeactivate)}
        title="Deactivate customer"
        description={
          pendingDeactivate
            ? `Deactivate customer "${pendingDeactivate.name}"? This action cannot be undone.`
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
