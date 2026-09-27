import { useState, useEffect, useCallback } from 'react'
import PaymentForm from '../../components/sales/payments/PaymentForm'
import { getAuth } from '../../services/api'
import { salesService } from '../../services/salesService'
import { useToast } from '../../components/ui'
import {
  Alert, Badge, Button, ConfirmDialog, PageContainer, PageHeader, Pagination, Select, Table,
} from '../../components/ui'
import { space } from '../../lib/tokens'
import { PAGE_SIZE } from '../../lib/pagination'

const money = (v) => Number(v || 0).toFixed(2)

const statusTone = { Draft: 'warning', Posted: 'success' }

export default function PaymentsPage() {
  const toast = useToast()
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const canPost = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'

  const [payments, setPayments] = useState([])
  const [postedInvoices, setPostedInvoices] = useState([])
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const [busy, setBusy] = useState(false)

  const fetchPayments = useCallback(() => {
    const params = { page }
    if (statusFilter) params.status = statusFilter
    salesService.getPayments(params)
      .then(({ data }) => {
        if ((data.results || []).length === 0 && page > 1) {
          return salesService.getPayments({ ...params, page: 1 }).then((first) => {
            setPayments(first.data.results || [])
            setTotal(first.data.count ?? 0)
            setPage(1)
          })
        }
        setPayments(data.results || [])
        setTotal(data.count ?? 0)
      })
      .catch(() => setError('Failed to load payments. Please try again.'))
      .finally(() => setLoading(false))
  }, [statusFilter, page])

  const fetchPostedInvoices = useCallback(() => {
    salesService.getInvoices({ status: 'Posted', page_size: 100 })
      .then(({ data }) => setPostedInvoices(data.results || []))
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

  function requestDelete(payment) {
    setConfirm({
      title: 'Delete draft payment',
      description: `Delete draft payment "${payment.number}"?`,
      confirmLabel: 'Delete',
      tone: 'danger',
      action: () => runAction(payment, salesService.deletePayment, 'Failed to delete payment.'),
    })
  }

  function requestPost(payment) {
    setConfirm({
      title: 'Post payment',
      description: `Post payment "${payment.number}"? This will create a journal entry and cannot be undone.`,
      confirmLabel: 'Post',
      tone: 'default',
      action: () => runAction(payment, salesService.postPayment, 'Failed to post payment.'),
    })
  }

  async function runAction(payment, serviceCall, errorMessage) {
    setBusy(true)
    try {
      await serviceCall(payment.id)
      await fetchPayments()
    } catch (err) {
      toast.error(err.response?.data?.detail || errorMessage)
    } finally {
      setBusy(false)
      setConfirm(null)
    }
  }

  const columns = [
    { key: 'number', label: 'Number' },
    {
      key: 'invoice',
      label: 'Invoice',
      render: (p) => p.invoice?.number ?? '—',
    },
    {
      key: 'customer_name',
      label: 'Customer',
      render: (p) => p.customer_name || p.invoice?.customer?.name || '—',
    },
    { key: 'payment_date', label: 'Date' },
    { key: 'method', label: 'Method' },
    {
      key: 'amount',
      label: 'Amount',
      align: 'right',
      numeric: true,
      render: (p) => money(p.amount),
    },
    {
      key: 'status',
      label: 'Status',
      render: (p) => (
        <Badge tone={statusTone[p.status] || 'neutral'} size="sm" dot>
          {p.status}
        </Badge>
      ),
    },
    ...(canManage ? [{
      key: 'actions',
      label: 'Actions',
      isActions: true,
      render: (p) => (
        <div style={{ display: 'flex', gap: space[1], justifyContent: 'flex-end' }}>
          {p.status === 'Draft' && (
            <>
              <Button variant="ghost" size="sm" onClick={() => handleEdit(p)}>Edit</Button>
              <Button variant="dangerSoft" size="sm" onClick={() => requestDelete(p)}>Delete</Button>
            </>
          )}
          {p.status === 'Draft' && canPost && (
            <Button variant="secondary" size="sm" onClick={() => requestPost(p)}>Post</Button>
          )}
        </div>
      ),
    }] : []),
  ]

  return (
    <PageContainer>
      <PageHeader
        title="Payments"
        description="Record and post customer payments."
        breadcrumbs={[{ label: 'Sales' }, { label: 'Payments' }]}
        primaryAction={
          canManage ? (
            <Button variant="primary" onClick={handleOpenCreate}>New Payment</Button>
          ) : undefined
        }
      />

      <div style={{ display: 'flex', gap: space[3], alignItems: 'flex-end', marginBottom: space[4], flexWrap: 'wrap' }}>
        <div style={{ width: '200px' }}>
          <Select
            label="Status"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          >
            <option value="">All</option>
            <option value="Draft">Draft</option>
            <option value="Posted">Posted</option>
          </Select>
        </div>
      </div>

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      <Table
        columns={columns}
        data={payments}
        loading={loading}
        emptyTitle="No payments found"
        emptyDescription="Record a customer payment to get started."
        emptyAction={canManage ? <Button variant="primary" onClick={handleOpenCreate}>New Payment</Button> : undefined}
      />

      <Pagination
        page={page}
        pageSize={PAGE_SIZE}
        total={total}
        onPageChange={setPage}
        style={{ marginTop: space[3], justifyContent: 'flex-start' }}
      />

      <PaymentForm
        key={showModal ? (editing?.id ?? 'new-open') : (editing?.id ?? 'new-closed')}
        open={showModal}
        onClose={() => setShowModal(false)}
        payment={editing}
        invoices={postedInvoices}
        onSaved={fetchPayments}
      />

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
