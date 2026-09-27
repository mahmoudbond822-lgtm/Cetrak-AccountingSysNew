import { useState, useEffect, useCallback, useRef } from 'react'
import PurchaseInvoiceForm from '../../components/purchases/invoices/PurchaseInvoiceForm'
import { getAuth } from '../../services/api'
import { purchasesService } from '../../services/purchasesService'
import { useToast } from '../../components/ui'
import {
  Alert, Badge, Button, ConfirmDialog, PageContainer, PageHeader, Pagination, Select, Table,
} from '../../components/ui'
import { space } from '../../lib/tokens'
import { PAGE_SIZE } from '../../lib/pagination'

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

const statusTone = { Draft: 'warning', Posted: 'success' }

export default function PurchaseInvoicesPage() {
  const toast = useToast()
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const canPost = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'

  const [invoices, setInvoices] = useState([])
  const [vendors, setVendors] = useState([])
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [notice, setNotice] = useState('')
  const [confirm, setConfirm] = useState(null)
  const [busy, setBusy] = useState(false)
  const previewRef = useRef('')

  const fetchInvoices = useCallback(() => {
    const params = { page }
    if (statusFilter) params.status = statusFilter
    purchasesService.getInvoices(params)
      .then(({ data }) => {
        if ((data.results || []).length === 0 && page > 1) {
          return purchasesService.getInvoices({ ...params, page: 1 }).then((first) => {
            setInvoices(first.data.results || [])
            setTotal(first.data.count ?? 0)
            setPage(1)
          })
        }
        setInvoices(data.results || [])
        setTotal(data.count ?? 0)
      })
      .catch(() => setError('Failed to load invoices. Please try again.'))
      .finally(() => setLoading(false))
  }, [statusFilter, page])

  const fetchVendors = useCallback(() => {
    purchasesService.getVendors({ page_size: 100 })
      .then(({ data }) => setVendors(data.results || []))
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

  function requestDelete(invoice) {
    setConfirm({
      title: 'Delete draft invoice',
      description: `Delete draft invoice "${invoice.number}"?`,
      confirmLabel: 'Delete',
      tone: 'danger',
      action: () => runAction(invoice, purchasesService.deleteInvoice, 'Failed to delete invoice.'),
    })
  }

  function requestPost(invoice) {
    setConfirm({
      title: 'Post invoice',
      description: `Post invoice "${invoice.number}"? This will create a journal entry and cannot be undone.`,
      confirmLabel: 'Post',
      tone: 'default',
      action: () => runAction(invoice, purchasesService.postInvoice, 'Failed to post invoice.'),
    })
  }

  async function runAction(invoice, serviceCall, errorMessage) {
    setBusy(true)
    try {
      await serviceCall(invoice.id)
      await fetchInvoices()
    } catch (err) {
      toast.error(err.response?.data?.detail || errorMessage)
    } finally {
      setBusy(false)
      setConfirm(null)
    }
  }

  const columns = [
    { key: 'number', label: 'Number' },
    { key: 'vendor_name', label: 'Vendor' },
    { key: 'invoice_date', label: 'Date' },
    { key: 'due_date', label: 'Due date' },
    {
      key: 'total',
      label: 'Total',
      align: 'right',
      numeric: true,
      render: (i) => money(i.total),
    },
    {
      key: 'outstanding_balance',
      label: 'Outstanding',
      align: 'right',
      numeric: true,
      render: (i) => money(i.outstanding_balance),
    },
    {
      key: 'status',
      label: 'Status',
      render: (i) => (
        <Badge tone={statusTone[i.status] || 'neutral'} size="sm" dot>
          {i.status}
        </Badge>
      ),
    },
    ...(canManage ? [{
      key: 'actions',
      label: 'Actions',
      isActions: true,
      render: (i) => (
        <div style={{ display: 'flex', gap: space[1], justifyContent: 'flex-end' }}>
          {i.status === 'Draft' && (
            <>
              <Button variant="ghost" size="sm" onClick={() => handleEdit(i)}>Edit</Button>
              <Button variant="dangerSoft" size="sm" onClick={() => requestDelete(i)}>Delete</Button>
            </>
          )}
          {i.status === 'Draft' && canPost && (
            <Button variant="secondary" size="sm" onClick={() => requestPost(i)}>Post</Button>
          )}
        </div>
      ),
    }] : []),
  ]

  return (
    <PageContainer>
      <PageHeader
        title="Purchase Invoices"
        description="Record, edit and post supplier invoices."
        breadcrumbs={[{ label: 'Purchases' }, { label: 'Purchase Invoices' }]}
        primaryAction={
          canManage ? (
            <Button variant="primary" onClick={handleOpenCreate}>New Purchase Invoice</Button>
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
        data={invoices}
        loading={loading}
        emptyTitle="No purchase invoices found"
        emptyDescription="Record a supplier invoice to get started."
        emptyAction={canManage ? <Button variant="primary" onClick={handleOpenCreate}>New Purchase Invoice</Button> : undefined}
      />

      <Pagination
        page={page}
        pageSize={PAGE_SIZE}
        total={total}
        onPageChange={setPage}
        style={{ marginTop: space[3], justifyContent: 'flex-start' }}
      />

      <PurchaseInvoiceForm
        key={showModal ? (editing?.id ?? 'new-open') : (editing?.id ?? 'new-closed')}
        open={showModal}
        onClose={() => setShowModal(false)}
        invoice={editing}
        vendors={vendors}
        nextNumber={nextInvoiceNumber(invoices)}
        onSaved={handleSaved}
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
