import { useState, useEffect, useCallback, useRef } from 'react'
import SalesNav from '../../components/Layout/SalesNav'
import Table from '../../components/shared/Table'
import Button from '../../components/shared/Button'
import CustomerModal from '../../components/sales/customers/CustomerModal'
import { getAuth } from '../../services/api'
import { salesService } from '../../services/salesService'

const pageStyle = { maxWidth: '960px', margin: '0 auto', padding: '1.5rem' }
const headerStyle = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600 }
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}

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
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [notice, setNotice] = useState('')
  const previewRef = useRef('')

  const fetchCustomers = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await salesService.getCustomers()
      setCustomers(data)
    } catch {
      setError('Failed to load customers. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

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

  async function handleDeactivate(customer) {
    if (!window.confirm(`Deactivate customer "${customer.name}"? This action cannot be undone.`)) return
    try {
      await salesService.deleteCustomer(customer.id)
      fetchCustomers()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to deactivate customer.'
      alert(msg)
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
      render: (c) => (c.is_active ? 'Active' : 'Inactive'),
    },
    ...(canManage ? [{
      key: 'actions',
      label: 'Actions',
      render: (c) => (
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Button variant="secondary" onClick={() => handleEdit(c)}>Edit</Button>
          {c.is_active && (
            <Button variant="danger" onClick={() => handleDeactivate(c)}>Deactivate</Button>
          )}
        </div>
      ),
    }] : []),
  ]

  return (
    <div>
      <SalesNav />
      <div style={pageStyle}>
        <div style={headerStyle}>
          <h1 style={titleStyle}>Customers</h1>
          {canManage && (
            <Button variant="primary" onClick={handleOpenCreate}>Create Customer</Button>
          )}
        </div>

        {notice && (
          <div style={{ padding: '0.75rem 1rem', background: '#F0F8F0', border: '1px solid #4CAF50', borderRadius: '6px', marginBottom: '1rem', color: '#2E7D32', fontSize: '0.875rem' }}>
            {notice}
          </div>
        )}

        {error && (
          <div style={{ padding: '0.75rem 1rem', background: '#FFF3F3', border: '1px solid #F44336', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        {loading ? (
          <div>
            {[...Array(4)].map((_, i) => (
              <div key={i} style={skeletonStyle} />
            ))}
          </div>
        ) : (
          <Table columns={columns} data={customers} emptyMessage="No customers found." />
        )}

        <CustomerModal
          open={showModal}
          onClose={() => setShowModal(false)}
          customer={editing}
          nextCode={nextCustomerCode(customers)}
          onSaved={handleSaved}
        />
      </div>
    </div>
  )
}