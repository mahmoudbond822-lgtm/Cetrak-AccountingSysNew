import { useState, useEffect, useCallback } from 'react'
import InventoryNav from '../../components/Layout/InventoryNav'
import Table from '../../components/shared/Table'
import Button from '../../components/shared/Button'
import Input from '../../components/shared/Input'
import ProductModal from '../../components/inventory/products/ProductModal'
import { getAuth } from '../../services/api'
import { inventoryService } from '../../services/inventoryService'

const pageStyle = { maxWidth: '960px', margin: '0 auto', padding: '1.5rem' }
const headerStyle = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600 }
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}
const searchStyle = { width: '240px', marginBottom: '1rem' }

export default function ProductsPage() {
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)

  const fetchProducts = useCallback(() => {
    inventoryService.getProducts()
      .then(({ data }) => setProducts(data))
      .catch(() => setError('Failed to load products. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { fetchProducts() }, [fetchProducts])

  function handleOpenCreate() {
    setEditing(null)
    setShowModal(true)
  }

  function handleEdit(product) {
    setEditing(product)
    setShowModal(true)
  }

  async function handleDeactivate(product) {
    if (!window.confirm(`Deactivate product "${product.sku}"? This action cannot be undone if stock exists.`)) return
    try {
      await inventoryService.deleteProduct(product.id)
      fetchProducts()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to deactivate product.'
      alert(msg)
    }
  }

  const filtered = products.filter((p) =>
    !query || p.sku.toLowerCase().includes(query.toLowerCase()) ||
    p.name.toLowerCase().includes(query.toLowerCase())
  )

  const columns = [
    { key: 'sku', label: 'SKU' },
    { key: 'name', label: 'Name' },
    { key: 'unit', label: 'Unit' },
    {
      key: 'is_active',
      label: 'Status',
      render: (v) => (v.is_active ? 'Active' : 'Inactive'),
    },
    ...(canManage ? [{
      key: 'actions',
      label: 'Actions',
      render: (v) => (
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Button variant="secondary" onClick={() => handleEdit(v)}>Edit</Button>
          {v.is_active && (
            <Button variant="danger" onClick={() => handleDeactivate(v)}>Deactivate</Button>
          )}
        </div>
      ),
    }] : []),
  ]

  return (
    <div>
      <InventoryNav />
      <div style={pageStyle}>
        <div style={headerStyle}>
          <h1 style={titleStyle}>Products</h1>
          {canManage && (
            <Button variant="primary" onClick={handleOpenCreate}>Create Product</Button>
          )}
        </div>

        {error && (
          <div style={{ padding: '0.75rem 1rem', background: '#FFF3F3', border: '1px solid #F44336', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        <div style={searchStyle}>
          <Input placeholder="Search SKU or name..." value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>

        {loading ? (
          <div>
            {[...Array(4)].map((_, i) => (
              <div key={i} style={skeletonStyle} />
            ))}
          </div>
        ) : (
          <Table columns={columns} data={filtered} emptyMessage="No products found." />
        )}

        <ProductModal
          open={showModal}
          onClose={() => setShowModal(false)}
          product={editing}
          onSaved={fetchProducts}
        />
      </div>
    </div>
  )
}