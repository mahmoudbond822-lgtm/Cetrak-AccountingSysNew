import { useState, useEffect, useCallback, useRef } from 'react'
import VendorModal from '../../components/purchases/vendors/VendorModal'
import { getAuth } from '../../services/api'
import { purchasesService } from '../../services/purchasesService'
import { useToast } from '../../components/ui'
import {
  Alert, Badge, Button, ConfirmDialog, PageContainer, PageHeader, Pagination, Table,
} from '../../components/ui'
import { space } from '../../lib/tokens'
import { PAGE_SIZE } from '../../lib/pagination'

function nextVendorCode(vendors) {
  const used = new Set()
  for (const v of vendors || []) {
    const m = /^VEN-(\d+)$/.exec(v.code || '')
    if (m) used.add(parseInt(m[1], 10))
  }
  let n = 1
  while (used.has(n)) n += 1
  return `VEN-${String(n).padStart(4, '0')}`
}

export default function VendorsPage() {
  const toast = useToast()
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const [vendors, setVendors] = useState([])
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

  const fetchVendors = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await purchasesService.getVendors({ page })
      if ((data.results || []).length === 0 && page > 1) {
        const first = await purchasesService.getVendors({ page: 1 })
        setVendors(first.data.results || [])
        setTotal(first.data.count ?? 0)
        setPage(1)
      } else {
        setVendors(data.results || [])
        setTotal(data.count ?? 0)
      }
    } catch {
      setError('Failed to load vendors. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { fetchVendors() }, [fetchVendors])

  function handleOpenCreate() {
    previewRef.current = nextVendorCode(vendors)
    setNotice('')
    setEditing(null)
    setShowModal(true)
  }

  async function handleSaved(saved) {
    await fetchVendors()
    if (saved?.code && saved.code !== previewRef.current) {
      setNotice(`Saved with auto-assigned code ${saved.code} (preview was ${previewRef.current}).`)
    }
  }

  function handleEdit(vendor) {
    setEditing(vendor)
    setShowModal(true)
  }

  function handleDeactivate(vendor) {
    setPendingDeactivate(vendor)
  }

  async function confirmDeactivate() {
    const vendor = pendingDeactivate
    if (!vendor) return
    setDeactivating(true)
    try {
      await purchasesService.deleteVendor(vendor.id)
      await fetchVendors()
      toast.success(`Vendor "${vendor.name}" deactivated.`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to deactivate vendor.')
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
      render: (v) => (
        <Badge tone={v.is_active ? 'success' : 'neutral'} size="sm" dot>
          {v.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    ...(canManage ? [{
      key: 'actions',
      label: 'Actions',
      isActions: true,
      render: (v) => (
        <div style={{ display: 'flex', gap: space[1], justifyContent: 'flex-end' }}>
          <Button variant="ghost" size="sm" onClick={() => handleEdit(v)}>Edit</Button>
          {v.is_active && (
            <Button variant="dangerSoft" size="sm" onClick={() => handleDeactivate(v)}>
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
        title="Vendors"
        description="Manage your supplier directory and contact details."
        breadcrumbs={[{ label: 'Purchases' }, { label: 'Vendors' }]}
        primaryAction={
          canManage ? (
            <Button variant="primary" onClick={handleOpenCreate}>Create Vendor</Button>
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
        data={vendors}
        loading={loading}
        emptyTitle="No vendors yet"
        emptyDescription="Create your first vendor to start recording purchase invoices."
        emptyAction={canManage ? <Button variant="primary" onClick={handleOpenCreate}>Create Vendor</Button> : undefined}
      />

      <Pagination
        page={page}
        pageSize={PAGE_SIZE}
        total={total}
        onPageChange={setPage}
        style={{ marginTop: space[3], justifyContent: 'flex-start' }}
      />

      <VendorModal
        open={showModal}
        onClose={() => setShowModal(false)}
        vendor={editing}
        nextCode={nextVendorCode(vendors)}
        onSaved={handleSaved}
      />

      <ConfirmDialog
        open={Boolean(pendingDeactivate)}
        title="Deactivate vendor"
        description={
          pendingDeactivate
            ? `Deactivate vendor "${pendingDeactivate.name}"? This action cannot be undone.`
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
