import { useState, useEffect, useCallback, useRef } from 'react'
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
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const [vendors, setVendors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [notice, setNotice] = useState('')
  const previewRef = useRef('')

  const fetchVendors = useCallback(() => {
    purchasesService.getVendors()
      .then(({ data }) => setVendors(data))
      .catch(() => setError('Failed to load vendors. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

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
          <Table columns={columns} data={vendors} emptyMessage="No vendors found." />
        )}

        <VendorModal
          open={showModal}
          onClose={() => setShowModal(false)}
          vendor={editing}
          nextCode={nextVendorCode(vendors)}
          onSaved={handleSaved}
        />
      </div>
    </div>
  )
}