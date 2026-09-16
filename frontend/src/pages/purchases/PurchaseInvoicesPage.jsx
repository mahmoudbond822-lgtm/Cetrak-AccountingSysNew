import { useState, useEffect, useCallback, useRef } from 'react'
import PurchasesNav from '../../components/Layout/PurchasesNav'
import Table from '../../components/shared/Table'
import Button from '../../components/shared/Button'
import PurchaseInvoiceForm from '../../components/purchases/invoices/PurchaseInvoiceForm'
import { getAuth } from '../../services/api'
import { purchasesService } from '../../services/purchasesService'

const pageStyle = { maxWidth: '960px', margin: '0 auto', padding: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600 }
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}
const money = (v) => Number(v || 0).toFixed(2)

function nextInvoiceNumber(invoices) {
  const used = new Set()
  for (const inv of invoices || []) {
    const m = /^INV-(\d+)$/.exec(inv.number || '')
    if (m) used.add(parseInt(m[1], 10))
  }
  let n = 1
  while (used.has(n)) n += 1
  return `INV-${String(n).padStart(4, '0')}`
}

export default function PurchaseInvoicesPage() {
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const canPost = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'

  const [invoices, setInvoices] = useState([])
  const [vendors, setVendors] = useState([])
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [notice, setNotice] = useState('')
  const previewRef = useRef('')

  const fetchInvoices = useCallback(() => {
    purchasesService.getInvoices(statusFilter ? { status: statusFilter } : {})
      .then(({ data }) => setInvoices(data))
      .catch(() => setError('Failed to load invoices. Please try again.'))
      .finally(() => setLoading(false))
  }, [statusFilter])

  const fetchVendors = useCallback(() => {
    purchasesService.getVendors()
      .then(({ data }) => setVendors(data))
      .catch(() => { /* vendor list is optional for the invoice form */ })
  }, [])

  useEffect(() => { fetchInvoices() }, [fetchInvoices])
  useEffect(() => { fetchVendors() }, [fetchVendors])

  function handleOpenCreate() {
    previewRef.current = nextInvoiceNumber(invoices)
    setNotice('')
    setEditing(null)
    setShowModal(true)
  }

  function handleSaved(saved) {
    fetchInvoices()
    if (saved?.number && saved.number !== previewRef.current) {
      setNotice(`Saved with auto-assigned number ${saved.number} (preview was ${previewRef.current}).`)
    }
  }

  function handleEdit(invoice) {
    if (invoice.status !== 'Draft') return
    setEditing(invoice)
    setShowModal(true)
  }

  async function handleDelete(invoice) {
    if (!window.confirm(`Delete draft invoice "${invoice.number}"?`)) return
    try {
      await purchasesService.deleteInvoice(invoice.id)
      fetchInvoices()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete invoice.')
    }
  }

  async function handlePost(invoice) {
    if (!window.confirm(`Post invoice "${invoice.number}"? This will create a journal entry and cannot be undone.`)) return
    try {
      await purchasesService.postInvoice(invoice.id)
      fetchInvoices()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to post invoice.')
    }
  }

  const columns = [
    { key: 'number', label: 'Number' },
    { key: 'vendor_name', label: 'Vendor' },
    { key: 'invoice_date', label: 'Date' },
    { key: 'due_date', label: 'Due Date' },
    {
      key: 'total',
      label: 'Total',
      align: 'right',
      render: (i) => money(i.total),
    },
    {
      key: 'outstanding_balance',
      label: 'Outstanding',
      align: 'right',
      render: (i) => money(i.outstanding_balance),
    },
    {
      key: 'status',
      label: 'Status',
      render: (i) => (
        <span style={{ color: i.status === 'Posted' ? '#2E7D32' : '#555' }}>
          {i.status}
        </span>
      ),
    },
    ...(canManage ? [{
      key: 'actions',
      label: 'Actions',
      render: (i) => (
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {i.status === 'Draft' && (
            <>
              <Button variant="secondary" onClick={() => handleEdit(i)}>Edit</Button>
              <Button variant="danger" style={{ padding: '0.5rem' }} onClick={() => handleDelete(i)}>Delete</Button>
            </>
          )}
          {i.status === 'Draft' && canPost && (
            <Button variant="primary" style={{ padding: '0.5rem' }} onClick={() => handlePost(i)}>Post</Button>
          )}
        </div>
      ),
    }] : []),
  ]

  return (
    <div>
      <PurchasesNav />
      <div style={pageStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h1 style={titleStyle}>Purchase Invoices</h1>
          {canManage && (
            <Button variant="primary" onClick={handleOpenCreate}>New Invoice</Button>
          )}
        </div>

        <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <label style={{ fontSize: '0.875rem' }}>Status:</label>
          <select
            style={{ padding: '0.4rem 0.6rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.875rem' }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All</option>
            <option value="Draft">Draft</option>
            <option value="Posted">Posted</option>
          </select>
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
          <Table columns={columns} data={invoices} emptyMessage="No purchase invoices found." />
        )}

        <PurchaseInvoiceForm
          key={showModal ? (editing?.id ?? 'new-open') : (editing?.id ?? 'new-closed')}
          open={showModal}
          onClose={() => setShowModal(false)}
          invoice={editing}
          vendors={vendors}
          nextNumber={nextInvoiceNumber(invoices)}
          onSaved={handleSaved}
        />
      </div>
    </div>
  )
}