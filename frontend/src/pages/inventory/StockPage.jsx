import { useState, useEffect, useCallback } from 'react'
import ProductSelect from '../../components/inventory/ProductSelect'
import { inventoryService } from '../../services/inventoryService'
import {
  Alert, Card, CardBody, PageContainer, PageHeader, Pagination, Select, Skeleton, Table,
} from '../../components/ui'
import { font, space } from '../../lib/tokens'
import { PAGE_SIZE } from '../../lib/pagination'

const fmt = (v) => Number(v || 0).toFixed(4)

export default function StockPage() {
  const [balances, setBalances] = useState([])
  const [movements, setMovements] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [productId, setProductId] = useState('')
  const [movementType, setMovementType] = useState('')
  const [balancePage, setBalancePage] = useState(1)
  const [balanceTotal, setBalanceTotal] = useState(0)
  const [movementPage, setMovementPage] = useState(1)
  const [movementTotal, setMovementTotal] = useState(0)

  const fetchBalances = useCallback(() => {
    const params = { page: balancePage }
    if (productId) params.product_id = productId
    inventoryService.getBalances(params)
      .then(({ data }) => {
        if ((data.results || []).length === 0 && balancePage > 1) {
          return inventoryService.getBalances({ ...params, page: 1 }).then((first) => {
            setBalances(first.data.results || [])
            setBalanceTotal(first.data.count ?? 0)
            setBalancePage(1)
          })
        }
        setBalances(data.results || [])
        setBalanceTotal(data.count ?? 0)
      })
      .catch(() => setError('Failed to load stock balances.'))
  }, [productId, balancePage])

  const fetchMovements = useCallback(() => {
    const params = { page: movementPage }
    if (productId) params.product_id = productId
    if (movementType) params.movement_type = movementType
    inventoryService.getMovements(params)
      .then(({ data }) => {
        if ((data.results || []).length === 0 && movementPage > 1) {
          return inventoryService.getMovements({ ...params, page: 1 }).then((first) => {
            setMovements(first.data.results || [])
            setMovementTotal(first.data.count ?? 0)
            setMovementPage(1)
          })
        }
        setMovements(data.results || [])
        setMovementTotal(data.count ?? 0)
      })
      .catch(() => setError('Failed to load stock movements.'))
  }, [productId, movementType, movementPage])

  useEffect(() => {
    Promise.all([fetchBalances(), fetchMovements()])
      .finally(() => setLoading(false))
  }, [fetchBalances, fetchMovements])

  const balanceColumns = [
    { key: 'product_sku', label: 'SKU' },
    { key: 'product_name', label: 'Product' },
    { key: 'warehouse_name', label: 'Warehouse' },
    {
      key: 'quantity',
      label: 'Quantity',
      align: 'right',
      numeric: true,
      render: (v) => fmt(v.quantity),
    },
    {
      key: 'value',
      label: 'Value',
      align: 'right',
      numeric: true,
      render: (v) => fmt(v.value),
    },
    {
      key: 'moving_avg_cost',
      label: 'Avg Cost',
      align: 'right',
      numeric: true,
      render: (v) => fmt(v.moving_avg_cost),
    },
  ]

  const movementColumns = [
    { key: 'created_at', label: 'Date', render: (v) => new Date(v.created_at).toLocaleString() },
    { key: 'product_sku', label: 'SKU' },
    { key: 'product_name', label: 'Product' },
    { key: 'movement_type', label: 'Type', render: (v) => v.movement_type },
    {
      key: 'quantity',
      label: 'Qty',
      align: 'right',
      numeric: true,
      render: (v) => fmt(v.quantity),
    },
    {
      key: 'unit_cost',
      label: 'Unit Cost',
      align: 'right',
      numeric: true,
      render: (v) => fmt(v.unit_cost),
    },
    {
      key: 'value',
      label: 'Value',
      align: 'right',
      numeric: true,
      render: (v) => fmt(v.value),
    },
    {
      key: 'source',
      label: 'Source',
      render: (v) => v.purchase_invoice_num || v.sales_invoice_num || v.adjustment_num || '—',
    },
  ]

  return (
    <PageContainer>
      <PageHeader
        title="Stock"
        description="Current stock balances per warehouse and the full movement history."
        breadcrumbs={[{ label: 'Inventory' }, { label: 'Stock' }]}
      />

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      <div style={{ display: 'flex', gap: space[3], alignItems: 'flex-end', marginBottom: space[4], maxWidth: '600px', flexWrap: 'wrap' }}>
        <div style={{ width: '280px' }}>
          <ProductSelect
            label="Product"
            value={productId}
            onChange={(id) => { setProductId(id); setBalancePage(1); setMovementPage(1) }}
            placeholder="All products"
            includeEmpty
          />
        </div>
        <div style={{ width: '280px' }}>
          <Select
            label="Movement Type"
            value={movementType}
            onChange={(e) => { setMovementType(e.target.value); setMovementPage(1) }}
          >
            <option value="">All types</option>
            <option value="Receipt">Receipt</option>
            <option value="Issue">Issue</option>
            <option value="Adjustment">Adjustment</option>
          </Select>
        </div>
      </div>

      {loading ? (
        <Card>
          <CardBody>
            <Skeleton count={4} height="38px" />
          </CardBody>
        </Card>
      ) : (
        <>
          <div style={{ marginBottom: space[6] }}>
            <h2 style={{ fontSize: font.size.sectionTitle, fontWeight: font.weight.semibold, marginBottom: space[3] }}>
              Stock Balances
            </h2>
            <Table
              columns={balanceColumns}
              data={balances}
              emptyTitle="No stock balances"
              emptyDescription="Balances appear here once you post receipts or adjustments."
            />
            <Pagination
              page={balancePage}
              pageSize={PAGE_SIZE}
              total={balanceTotal}
              onPageChange={setBalancePage}
              style={{ marginTop: space[3], justifyContent: 'flex-start' }}
            />
          </div>
          <div style={{ marginBottom: space[6] }}>
            <h2 style={{ fontSize: font.size.sectionTitle, fontWeight: font.weight.semibold, marginBottom: space[3] }}>
              Stock Movements
            </h2>
            <Table
              columns={movementColumns}
              data={movements}
              emptyTitle="No stock movements"
              emptyDescription="Receipts, issues and adjustments will be listed here."
            />
            <Pagination
              page={movementPage}
              pageSize={PAGE_SIZE}
              total={movementTotal}
              onPageChange={setMovementPage}
              style={{ marginTop: space[3], justifyContent: 'flex-start' }}
            />
          </div>
        </>
      )}
    </PageContainer>
  )
}
