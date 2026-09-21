import { useState } from 'react'
import { Modal, Button, Input, Alert } from '../../ui'
import { purchasesService } from '../../../services/purchasesService'

const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }

const emptyForm = {
  code: '',
  name: '',
  email: '',
  phone: '',
  address: '',
  tax_id: '',
}

export default function VendorModal({ open, onClose, vendor, nextCode, onSaved }) {
  const [form, setForm] = useState(vendor ? {
    code: vendor.code || '',
    name: vendor.name || '',
    email: vendor.email || '',
    phone: vendor.phone || '',
    address: vendor.address || '',
    tax_id: vendor.tax_id || '',
  } : emptyForm)
  const [saving, setSaving] = useState(false)
  const [formErrors, setFormErrors] = useState({})

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setFormErrors({})
    const payload = {
      name: form.name,
      email: form.email || null,
      phone: form.phone || null,
      address: form.address || null,
      tax_id: form.tax_id || null,
    }
    try {
      if (vendor) {
        await purchasesService.updateVendor(vendor.id, payload)
        onSaved()
      } else {
        const res = await purchasesService.createVendor(payload)
        onSaved(res?.data)
      }
      onClose()
    } catch (err) {
      const data = err.response?.data
      if (typeof data === 'object') {
        setFormErrors(data)
      } else {
        setFormErrors({ general: 'Failed to save vendor.' })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={vendor ? 'Edit Vendor' : 'Create Vendor'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleSubmit} disabled={saving}>
            {saving ? 'Saving...' : vendor ? 'Update' : 'Create'}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        {vendor && (
          <div style={fieldStyle}>
            <Input label="Code" value={form.code} readOnly />
          </div>
        )}
        {!vendor && (
          <div style={fieldStyle}>
            <Input label="Code (auto-assigned)" value={nextCode || 'VEN-0001'} readOnly />
          </div>
        )}
        <div style={fieldStyle}>
          <Input label="Name *" name="name" value={form.name} onChange={handleChange} error={formErrors.name} required />
        </div>
        <div style={fieldStyle}>
          <Input label="Email" type="email" name="email" value={form.email} onChange={handleChange} error={formErrors.email} />
        </div>
        <div style={fieldStyle}>
          <Input label="Phone" name="phone" value={form.phone} onChange={handleChange} error={formErrors.phone} />
        </div>
        <div style={fieldStyle}>
          <Input label="Tax Identifier" name="tax_id" value={form.tax_id} onChange={handleChange} error={formErrors.tax_id} />
        </div>
        <div style={fieldStyle}>
          <Input label="Address" name="address" value={form.address} onChange={handleChange} error={formErrors.address} />
        </div>
        {formErrors.general && (
          <Alert tone="error" style={{ marginBottom: '1rem' }}>{formErrors.general}</Alert>
        )}
      </form>
    </Modal>
  )
}