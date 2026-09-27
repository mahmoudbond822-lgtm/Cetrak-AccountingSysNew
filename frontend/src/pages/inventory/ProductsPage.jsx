import { useState, useEffect, useCallback, useRef } from 'react'
import ProductModal from '../../components/inventory/products/ProductModal'
import { getAuth } from '../../services/api'
import { inventoryService } from '../../services/inventoryService'
import { useToast } from '../../components/ui'
import {
  Alert, Badge, Button, ConfirmDialog, Input, PageContainer, PageHeader, Pagination, Table,
} from '../../components/ui'
import { space } from '../../lib/tokens'
import { PAGE_SIZE } from '../../lib/pagination'

export default function ProductsPage() {
  const toast = useToast()
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const [busy, setBusy] = useState(false)
  const searchTimer = useRef(null)

  const fetchProducts = useCallback(() => {
    const params = { page }
    if (query) params.search = query
    inventoryService.getProducts(params)
      .then(({ data }) => {
        if ((data.results || []).length === 0 && page > 1) {
          return inventoryService.getProducts({ ...params, page: 1 }).then((first) => {
            setProducts(first.data.results || [])
            setTotal(first.data.count ?? 0)
            setPage(1)
          })
        }
        setProducts(data.results || [])
        setTotal(data.count ?? 0)
      })
      .catch(() => setError('Failed to load products. Please try again.'))
      .finally(() => setLoading(false))
  }, [query, page])

  useEffect(() => { fetchProducts() }, [fetchProducts])

  useEffect(() => () => clearTimeout(searchTimer.current), [])

  function handleSearchChange(value) {
    setSearchInput(value)
    clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => {
      setQuery(value.trim())
      setPage(1)
    }, 300)
  }

  function handleOpenCreate() {
    setEditing(null)
    setShowModal(true)
  }

  function handleEdit(product) {
    setEditing(product)
    setShowModal(true)
  }

  function requestDeactivate(product) {
    setConfirm({
      title: 'Deactivate product',
      description: `Deactivate product "${product.sku}"? This action cannot be undone if stock exists.`,
      confirmLabel: 'Deactivate',
      tone: 'danger',
      action: () => runAction(product, inventoryService.deleteProduct, 'Failed to deactivate product.'),
    })
  }

  async function runAction(product, serviceCall, errorMessage) {
    setBusy(true)
    try {
      await serviceCall(product.id)
      await fetchProducts()
    } catch (err) {
      toast.error(err.response?.data?.detail || errorMessage)
    } finally {
      setBusy(false)
      setConfirm(null)
    }
  }

  const columns = [
    { key: 'sku', label: 'SKU' },
    { key: 'name', label: 'Name' },
    { key: 'unit', label: 'Unit' },
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
            <Button variant="dangerSoft" size="sm" onClick={() => requestDeactivate(v)}>
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
        title="Products"
        description="Manage your product catalogue, units and stock-keeping codes."
        breadcrumbs={[{ label: 'Inventory' }, { label: 'Products' }]}
        primaryAction={
          canManage ? (
            <Button variant="primary" onClick={handleOpenCreate}>Create Product</Button>
          ) : undefined
        }
      />

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      <div style={{ width: '240px', marginBottom: space[4] }}>
        <Input
          placeholder="Search SKU or name..."
          value={searchInput}
          onChange={(e) => handleSearchChange(e.target.value)}
        />
      </div>

      <Table
        columns={columns}
        data={products}
        loading={loading}
        emptyTitle="No products found"
        emptyDescription="Create your first product to start tracking stock."
        emptyAction={canManage ? <Button variant="primary" onClick={handleOpenCreate}>Create Product</Button> : undefined}
      />

      <Pagination
        page={page}
        pageSize={PAGE_SIZE}
        total={total}
        onPageChange={setPage}
        style={{ marginTop: space[3], justifyContent: 'flex-start' }}
      />

      <ProductModal
        open={showModal}
        onClose={() => setShowModal(false)}
        product={editing}
        onSaved={fetchProducts}
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
