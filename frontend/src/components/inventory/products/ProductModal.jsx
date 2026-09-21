import { useState } from 'react'
import { Modal, Button, Input, Alert } from '../../ui'
import { inventoryService } from '../../../services/inventoryService'

const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }

function seededForm(product) {
  if (!product) {
    return { sku: '', name: '', unit: '', is_active: true }
  }
  return {
    sku: product.sku,
    name: product.name,
    unit: product.unit,
    is_active: product.is_active,
  }
}

export default function ProductModal({ open, onClose, product, onSaved }) {
  const [form, setForm] = useState(seededForm(product))
  const [saving, setSaving] = useState(false)
  const [formErrors, setFormErrors] = useState({})

  function handleChange(e) {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const payload = () => ({
    sku: form.sku,
    name: form.name,
    unit: form.unit,
    is_active: form.is_active,
  })

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setFormErrors({})
    try {
      if (product) {
        await inventoryService.updateProduct(product.id, payload())
      } else {
        await inventoryService.createProduct(payload())
      }
      onSaved()
      onClose()
    } catch (err) {
      const data = err.response?.data
      if (typeof data === 'object') {
        setFormErrors(data)
      } else {
        setFormErrors({ general: 'Failed to save product.' })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={product ? `Edit Product ${product.sku}` : 'New Product'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleSubmit} disabled={saving}>
            {saving ? 'Saving...' : product ? 'Save Changes' : 'Create Product'}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div style={fieldStyle}>
          <Input label="SKU *" name="sku" value={form.sku} onChange={handleChange} error={formErrors.sku} required />
        </div>
        <div style={fieldStyle}>
          <Input label="Name *" name="name" value={form.name} onChange={handleChange} error={formErrors.name} required />
        </div>
        <div style={fieldStyle}>
          <Input label="Unit *" name="unit" value={form.unit} onChange={handleChange} error={formErrors.unit} required placeholder="pcs, kg, box..." />
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem' }}>
          <input type="checkbox" name="is_active" checked={form.is_active} onChange={handleChange} />
          Active
        </label>
        <Input label="Product ID" name="id" value={product ? product.id : ''} disabled />
        {formErrors.general && (
          <Alert tone="error" style={{ marginTop: '1rem' }}>{formErrors.general}</Alert>
        )}
      </form>
    </Modal>
  )
}