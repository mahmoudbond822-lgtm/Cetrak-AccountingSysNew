import { useState, useEffect, useCallback } from 'react'
import PurchasesNav from '../../components/Layout/PurchasesNav'
import Table from '../../components/shared/Table'
import Button from '../../components/shared/Button'
import PurchasePaymentForm from '../../components/purchases/payments/PurchasePaymentForm'
import { getAuth } from '../../services/api'
import { purchasesService } from '../../services/purchasesService'

const pageStyle = { maxWidth: '960px', margin: '0 auto', padding: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600 }
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}
const money = (v) => Number(v || 0).toFixed(2)

export default function PurchasePaymentsPage() {
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const canPost = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'

  const [payments, setPayments] = useState([])
  const [postedInvoices, setPostedInvoices] = useState([])
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)

  const fetchPayments = useCallback(() => {
    purchasesService.getPayments(statusFilter ? { status: statusFilter } : {})
      .then(({ data }) => setPayments(data))
      .catch(() => setError('Failed to load payments. Please try again.'))
      .finally(() => setLoading(false))
  }, [statusFilter])

  const fetchPostedInvoices = useCallback(() => {
    purchasesService.getInvoices({ status: 'Posted' })
      .then(({ data }) => setPostedInvoices(data))
      .catch(() => { /* posted invoice list is optional for the payment form */ })
  }, [])

  useEffect(() => { fetchPayments() }, [fetchPayments])
  useEffect(() => { fetchPostedInvoices() }, [fetchPostedInvoices])

  function handleOpenCreate() {
    setEditing(null)
    setShowModal(true)
  }

  function handleEdit(payment) {
    if (payment.status !== 'Draft') return
    setEditing(payment)
    setShowModal(true)
  }

  async function handleDelete(payment) {
    if (!window.confirm(`Delete draft payment "${payment.number}"?`)) return
    try {
      await purchasesService.deletePayment(payment.id)
      fetchPayments()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete payment.')
    }
  }

  async function handlePost(payment) {
    if (!window.confirm(`Post payment "${payment.number}"? This will create a journal entry and cannot be undone.`)) return
    try {
      await purchasesService.postPayment(payment.id)
      fetchPayments()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to post payment.')
    }
  }

  const columns = [
    { key: 'number', label: 'Number' },
    {
      key: 'purchase_invoice',
      label: 'Invoice',
      render: (p) => p.purchase_invoice?.number ?? '—',
    },
    {
      key: 'vendor_name',
      label: 'Vendor',
      render: (p) => p.vendor_name,
    },
    { key: 'payment_date', label: 'Date' },
    { key: 'method', label: 'Method' },
    {
      key: 'amount',
      label: 'Amount',
      align: 'right',
      render: (p) => money(p.amount),
    },
    {
      key: 'status',
      label: 'Status',
      render: (p) => (
        <span style={{ color: p.status === 'Posted' ? '#2E7D32' : '#555' }}>
          {p.status}
        </span>
      ),
    },
    ...(canManage ? [{
      key: 'actions',
      label: 'Actions',
      render: (p) => (
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {p.status === 'Draft' && (
            <>
              <Button variant="secondary" onClick={() => handleEdit(p)}>Edit</Button>
              <Button variant="danger" style={{ padding: '0.5rem' }} onClick={() => handleDelete(p)}>Delete</Button>
            </>
          )}
          {p.status === 'Draft' && canPost && (
            <Button variant="primary" style={{ padding: '0.5rem' }} onClick={() => handlePost(p)}>Post</Button>
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
          <h1 style={titleStyle}>Payments</h1>
          {canManage && (
            <Button variant="primary" onClick={handleOpenCreate}>New Payment</Button>
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
          <Table columns={columns} data={payments} emptyMessage="No payments found." />
        )}

        <PurchasePaymentForm
          key={showModal ? (editing?.id ?? 'new-open') : (editing?.id ?? 'new-closed')}
          open={showModal}
          onClose={() => setShowModal(false)}
          payment={editing}
          invoices={postedInvoices}
          onSaved={fetchPayments}
        />
      </div>
    </div>
  )
}