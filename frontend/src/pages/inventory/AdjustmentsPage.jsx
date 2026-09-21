import { useState, useEffect, useCallback } from 'react'
import AdjustmentForm from '../../components/inventory/adjustments/AdjustmentForm'
import { getAuth } from '../../services/api'
import { inventoryService } from '../../services/inventoryService'
import { useToast } from '../../components/ui'
import {
  Alert, Badge, Button, ConfirmDialog, PageContainer, PageHeader, Table,
} from '../../components/ui'
import { space } from '../../lib/tokens'

const statusTone = { Draft: 'warning', Posted: 'success' }

export default function AdjustmentsPage() {
  const toast = useToast()
  const { activeTenantRole } = getAuth()
  const canManage = activeTenantRole === 'Admin' || activeTenantRole === 'Accountant'
  const [adjustments, setAdjustments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const [busy, setBusy] = useState(false)

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

  function requestPost(adjustment) {
    setConfirm({
      title: 'Post adjustment',
      description: `Post adjustment "${adjustment.number}"? This posts a balanced journal entry and changes stock.`,
      confirmLabel: 'Post',
      tone: 'default',
      action: () => runAction(adjustment, inventoryService.postAdjustment, 'Failed to post adjustment.'),
    })
  }

  function requestDelete(adjustment) {
    setConfirm({
      title: 'Delete draft adjustment',
      description: `Delete draft adjustment "${adjustment.number}"?`,
      confirmLabel: 'Delete',
      tone: 'danger',
      action: () => runAction(adjustment, inventoryService.deleteAdjustment, 'Failed to delete adjustment.'),
    })
  }

  async function runAction(adjustment, serviceCall, errorMessage) {
    setBusy(true)
    try {
      await serviceCall(adjustment.id)
      await fetchAdjustments()
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
      key: 'status',
      label: 'Status',
      render: (v) => (
        <Badge tone={statusTone[v.status === 'Posted' ? 'Posted' : 'Draft']} size="sm" dot>
          {v.status === 'Posted' ? 'Posted' : 'Draft'}
        </Badge>
      ),
    },
    { key: 'adjustment_date', label: 'Date' },
    { key: 'reason', label: 'Reason' },
    {
      key: 'lines',
      label: 'Lines',
      align: 'right',
      numeric: true,
      render: (v) => v.lines.length,
    },
    ...(canManage ? [{
      key: 'actions',
      label: 'Actions',
      isActions: true,
      render: (v) => (
        <div style={{ display: 'flex', gap: space[1], justifyContent: 'flex-end' }}>
          {v.status === 'Draft' ? (
            <>
              <Button variant="ghost" size="sm" onClick={() => handleEdit(v)}>Edit</Button>
              <Button variant="secondary" size="sm" onClick={() => requestPost(v)}>Post</Button>
              <Button variant="dangerSoft" size="sm" onClick={() => requestDelete(v)}>Delete</Button>
            </>
          ) : (
            <span style={{ fontSize: '0.8rem', color: 'var(--text)' }}>Posted</span>
          )}
        </div>
      ),
    }] : []),
  ]

  return (
    <PageContainer>
      <PageHeader
        title="Stock Adjustments"
        description="Create and post stock adjustments to keep quantities and values accurate."
        breadcrumbs={[{ label: 'Inventory' }, { label: 'Adjustments' }]}
        primaryAction={
          canManage ? (
            <Button variant="primary" onClick={handleOpenCreate}>New Adjustment</Button>
          ) : undefined
        }
      />

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      <Table
        columns={columns}
        data={adjustments}
        loading={loading}
        emptyTitle="No adjustments found"
        emptyDescription="Create a draft adjustment to correct stock quantities."
        emptyAction={canManage ? <Button variant="primary" onClick={handleOpenCreate}>New Adjustment</Button> : undefined}
      />

      <AdjustmentForm
        open={showModal}
        onClose={() => setShowModal(false)}
        adjustment={editing}
        onSaved={fetchAdjustments}
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
