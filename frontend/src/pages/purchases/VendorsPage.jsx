import { useState, useEffect, useCallback } from 'react'
import PurchasesNav from '../../components/Layout/PurchasesNav'
import Table from '../../components/shared/Table'
import Button from '../../components/shared/Button'
import VendorModal from '../../components/purchases/vendors/VendorModal'
import { getAuth } from '../../services/api'
import { purchasesService } from '../../services/purchasesService'

const pageStyle = { maxWidth: '960px', margin: '0 auto', padding: '1.5rem' }
const headerStyle = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600 }
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}

export default function VendorsPage() {
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const [vendors, setVendors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)

  const fetchVendors = useCallback(() => {
    purchasesService.getVendors()
      .then(({ data }) => setVendors(data))
      .catch(() => setError('Failed to load vendors. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { fetchVendors() }, [fetchVendors])

  function handleOpenCreate() {
    setEditing(null)
    setShowModal(true)
  }

  function handleEdit(vendor) {
    setEditing(vendor)
    setShowModal(true)
  }

  async function handleDeactivate(vendor) {
    if (!window.confirm(`Deactivate vendor "${vendor.name}"? This action cannot be undone.`)) return
    try {
      await purchasesService.deleteVendor(vendor.id)
      fetchVendors()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to deactivate vendor.'
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
      <PurchasesNav />
      <div style={pageStyle}>
        <div style={headerStyle}>
          <h1 style={titleStyle}>Vendors</h1>
          {canManage && (
            <Button variant="primary" onClick={handleOpenCreate}>Create Vendor</Button>
          )}
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
          <Table columns={columns} data={vendors} emptyMessage="No vendors found." />
        )}

        <VendorModal
          open={showModal}
          onClose={() => setShowModal(false)}
          vendor={editing}
          onSaved={fetchVendors}
        />
      </div>
    </div>
  )
}