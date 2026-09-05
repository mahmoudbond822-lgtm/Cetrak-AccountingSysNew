import { useState } from 'react'
import Modal from '../../shared/Modal'
import Button from '../../shared/Button'
import Input from '../../shared/Input'
import ProductSelect from '../ProductSelect'
import { inventoryService } from '../../../services/inventoryService'

const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }
const lineHeaderStyle = {
  display: 'grid', gridTemplateColumns: '1fr 1fr 40px',
  gap: '0.5rem', fontWeight: 600, fontSize: '0.75rem',
  padding: '0.25rem 0', borderBottom: '1px solid var(--border)',
}
const lineRowStyle = {
  display: 'grid', gridTemplateColumns: '1fr 1fr 40px',
  gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center',
}

function emptyLine() {
  return { key: crypto.randomUUID?.() ?? Math.random(), product_id: '', quantity: '1' }
}

function seededForm(adjustment) {
  if (!adjustment) {
    return {
      number: '',
      adjustment_date: '',
      reason: '',
      notes: '',
      lines: [emptyLine()],
    }
  }
  return {
    number: adjustment.number,
    adjustment_date: adjustment.adjustment_date,
    reason: adjustment.reason,
    notes: adjustment.notes || '',
    lines: adjustment.lines.map((l) => ({
      key: l.id,
      product_id: l.product_id,
      quantity: l.quantity,
    })),
  }
}

export default function AdjustmentForm({ open, onClose, adjustment, onSaved }) {
  const [form, setForm] = useState(seededForm(adjustment))
  const [saving, setSaving] = useState(false)
  const [formErrors, setFormErrors] = useState({})

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  function handleLineChange(key, field, value) {
    setForm((prev) => ({
      ...prev,
      lines: prev.lines.map((l) => (l.key === key ? { ...l, [field]: value } : l)),
    }))
  }

  function addLine() {
    setForm((prev) => ({ ...prev, lines: [...prev.lines, emptyLine()] }))
  }

  function removeLine(key) {
    setForm((prev) => ({ ...prev, lines: prev.lines.filter((l) => l.key !== key) }))
  }

  const payload = () => ({
    number: form.number,
    adjustment_date: form.adjustment_date,
    reason: form.reason,
    notes: form.notes || null,
    lines: form.lines
      .filter((l) => l.product_id && Number(l.quantity) !== 0)
      .map((l) => ({
        product_id: l.product_id,
        quantity: String(Number(l.quantity)),
      })),
  })

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setFormErrors({})
    try {
      if (adjustment) {
        await inventoryService.updateAdjustment(adjustment.id, payload())
      } else {
        await inventoryService.createAdjustment(payload())
      }
      onSaved()
      onClose()
    } catch (err) {
      const data = err.response?.data
      if (typeof data === 'object') {
        setFormErrors(data)
      } else {
        setFormErrors({ general: 'Failed to save adjustment.' })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={adjustment ? `Edit Adjustment ${adjustment.number}` : 'New Adjustment'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleSubmit} disabled={saving}>
            {saving ? 'Saving...' : adjustment ? 'Save Changes' : 'Create Adjustment'}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <Input label="Number *" name="number" value={form.number} onChange={handleChange} error={formErrors.number} required />
          <Input label="Adjustment Date *" type="date" name="adjustment_date" value={form.adjustment_date} onChange={handleChange} required />
        </div>
        <div style={fieldStyle}>
          <Input label="Reason *" name="reason" value={form.reason} onChange={handleChange} error={formErrors.reason} required />
        </div>

        <div style={{ marginTop: '1rem' }}>
          <div style={lineHeaderStyle}>
            <span>Product</span>
            <span>Quantity (+/−)</span>
            <span />
          </div>
          {form.lines.map((l) => (
            <div key={l.key} style={lineRowStyle}>
              <ProductSelect value={l.product_id} onChange={(v) => handleLineChange(l.key, 'product_id', v)} />
              <input
                style={{ padding: '0.4rem 0.6rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}
                type="number" step="any"
                value={l.quantity}
                onChange={(e) => handleLineChange(l.key, 'quantity', e.target.value)}
              />
              <Button variant="danger" style={{ padding: '0.25rem 0.5rem' }} onClick={() => removeLine(l.key)}>×</Button>
            </div>
          ))}
          <Button variant="secondary" onClick={addLine}>+ Add Line</Button>
        </div>

        <div style={{ ...fieldStyle, marginTop: '1rem' }}>
          <Input label="Notes" name="notes" value={form.notes} onChange={handleChange} />
        </div>
        {formErrors.general && (
          <div style={{ padding: '0.5rem', background: '#FFF3F3', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.8rem' }}>{formErrors.general}</div>
        )}
      </form>
    </Modal>
  )
}