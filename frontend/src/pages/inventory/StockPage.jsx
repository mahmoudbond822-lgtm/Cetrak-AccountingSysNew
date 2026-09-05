import { useState, useEffect, useCallback } from 'react'
import InventoryNav from '../../components/Layout/InventoryNav'
import Table from '../../components/shared/Table'
import ProductSelect from '../../components/inventory/ProductSelect'
import { inventoryService } from '../../services/inventoryService'

const pageStyle = { maxWidth: '1024px', margin: '0 auto', padding: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600, marginBottom: '1.5rem' }
const sectionStyle = { marginBottom: '2rem' }
const sectionTitleStyle = { fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.75rem' }
const filtersStyle = { display: 'flex', gap: '1rem', alignItems: 'flex-end', marginBottom: '1rem', maxWidth: '600px' }
const filterColStyle = { width: '280px' }
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}
const fmt = (v) => Number(v || 0).toFixed(4)

export default function StockPage() {
  const [balances, setBalances] = useState([])
  const [movements, setMovements] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [productId, setProductId] = useState('')
  const [movementType, setMovementType] = useState('')

  const fetchBalances = useCallback(() => {
    inventoryService.getBalances(productId ? { product_id: productId } : {})
      .then(({ data }) => setBalances(data))
      .catch(() => setError('Failed to load stock balances.'))
  }, [productId])

  const fetchMovements = useCallback(() => {
    const params = {}
    if (productId) params.product_id = productId
    if (movementType) params.movement_type = movementType
    inventoryService.getMovements(params)
      .then(({ data }) => setMovements(data))
      .catch(() => setError('Failed to load stock movements.'))
  }, [productId, movementType])

  useEffect(() => {
    Promise.all([fetchBalances(), fetchMovements()])
      .finally(() => setLoading(false))
  }, [fetchBalances, fetchMovements])

  const balanceColumns = [
    { key: 'product_sku', label: 'SKU' },
    { key: 'product_name', label: 'Product' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'quantity', label: 'Quantity', render: (v) => fmt(v.quantity) },
    { key: 'value', label: 'Value', render: (v) => fmt(v.value) },
    { key: 'moving_avg_cost', label: 'Avg Cost', render: (v) => fmt(v.moving_avg_cost) },
  ]

  const movementColumns = [
    { key: 'created_at', label: 'Date', render: (v) => new Date(v.created_at).toLocaleString() },
    { key: 'product_sku', label: 'SKU' },
    { key: 'product_name', label: 'Product' },
    { key: 'movement_type', label: 'Type', render: (v) => v.movement_type },
    { key: 'quantity', label: 'Qty', render: (v) => fmt(v.quantity) },
    { key: 'unit_cost', label: 'Unit Cost', render: (v) => fmt(v.unit_cost) },
    { key: 'value', label: 'Value', render: (v) => fmt(v.value) },
    {
      key: 'source',
      label: 'Source',
      render: (v) => v.purchase_invoice_num || v.sales_invoice_num || v.adjustment_num || '—',
    },
  ]

  return (
    <div>
      <InventoryNav />
      <div style={pageStyle}>
        <h1 style={titleStyle}>Stock</h1>

        {error && (
          <div style={{ padding: '0.75rem 1rem', background: '#FFF3F3', border: '1px solid #F44336', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        <div style={filtersStyle}>
          <div style={filterColStyle}>
            <ProductSelect
              label="Product"
              value={productId}
              onChange={setProductId}
              placeholder="All products"
              includeEmpty
            />
          </div>
          <div style={filterColStyle}>
            <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>Movement Type</label>
            <select
              style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.875rem', outline: 'none', width: '100%', boxSizing: 'border-box', background: '#fff', marginTop: '0.25rem' }}
              value={movementType}
              onChange={(e) => setMovementType(e.target.value)}
            >
              <option value="">All types</option>
              <option value="Receipt">Receipt</option>
              <option value="Issue">Issue</option>
              <option value="Adjustment">Adjustment</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div>
            {[...Array(3)].map((_, i) => (
              <div key={i} style={skeletonStyle} />
            ))}
          </div>
        ) : (
          <>
            <div style={sectionStyle}>
              <h2 style={sectionTitleStyle}>Stock Balances</h2>
              <Table columns={balanceColumns} data={balances} emptyMessage="No stock balances." />
            </div>
            <div style={sectionStyle}>
              <h2 style={sectionTitleStyle}>Stock Movements</h2>
              <Table columns={movementColumns} data={movements} emptyMessage="No stock movements." />
            </div>
          </>
        )}
      </div>
    </div>
  )
}