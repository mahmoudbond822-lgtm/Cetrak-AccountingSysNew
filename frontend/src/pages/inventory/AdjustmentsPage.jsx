import { useState, useEffect, useCallback } from 'react'
import InventoryNav from '../../components/Layout/InventoryNav'
import Table from '../../components/shared/Table'
import Button from '../../components/shared/Button'
import AdjustmentForm from '../../components/inventory/adjustments/AdjustmentForm'
import { getAuth } from '../../services/api'
import { inventoryService } from '../../services/inventoryService'

const pageStyle = { maxWidth: '1024px', margin: '0 auto', padding: '1.5rem' }
const headerStyle = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600 }
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}

export default function AdjustmentsPage() {
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const [adjustments, setAdjustments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)

  const fetchAdjustments = useCallback(() => {
    inventoryService.getAdjustments()
      .then(({ data }) => setAdjustments(data))
      .catch(() => setError('Failed to load adjustments. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { fetchAdjustments() }, [fetchAdjustments])

  function handleOpenCreate() {
    setEditing(null)
    setShowModal(true)
  }

  function handleEdit(adjustment) {
    setEditing(adjustment)
    setShowModal(true)
  }

  async function handlePost(adjustment) {
    if (!window.confirm(`Post adjustment "${adjustment.number}"? This posts a balanced journal entry and changes stock.`)) return
    try {
      await inventoryService.postAdjustment(adjustment.id)
      fetchAdjustments()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to post adjustment.'
      alert(msg)
    }
  }

  async function handleDelete(adjustment) {
    if (!window.confirm(`Delete draft adjustment "${adjustment.number}"?`)) return
    try {
      await inventoryService.deleteAdjustment(adjustment.id)
      fetchAdjustments()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to delete adjustment.'
      alert(msg)
    }
  }

  const columns = [
    { key: 'number', label: 'Number' },
    {
      key: 'status',
      label: 'Status',
      render: (v) => (v.status === 'Posted' ? 'Posted' : 'Draft'),
    },
    { key: 'adjustment_date', label: 'Date' },
    { key: 'reason', label: 'Reason' },
    {
      key: 'lines',
      label: 'Lines',
      render: (v) => v.lines.length,
    },
    ...(canManage ? [{
      key: 'actions',
      label: 'Actions',
      render: (v) => (
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {v.status === 'Draft' ? (
            <>
              <Button variant="secondary" onClick={() => handleEdit(v)}>Edit</Button>
              <Button variant="primary" onClick={() => handlePost(v)}>Post</Button>
              <Button variant="danger" onClick={() => handleDelete(v)}>Delete</Button>
            </>
          ) : (
            <span style={{ fontSize: '0.8rem', color: 'var(--text)' }}>Posted</span>
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
          <h1 style={titleStyle}>Stock Adjustments</h1>
          {canManage && (
            <Button variant="primary" onClick={handleOpenCreate}>New Adjustment</Button>
          )}
        </div>

        {error && (
          <div style={{ padding: '0.75rem 1rem', background: '#FFF3F3', border: '1px solid #F44336', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        {loading ? (
          <div>
            {[...Array(3)].map((_, i) => (
              <div key={i} style={skeletonStyle} />
            ))}
          </div>
        ) : (
          <Table columns={columns} data={adjustments} emptyMessage="No adjustments found." />
        )}

        <AdjustmentForm
          open={showModal}
          onClose={() => setShowModal(false)}
          adjustment={editing}
          onSaved={fetchAdjustments}
        />
      </div>
    </div>
  )
}