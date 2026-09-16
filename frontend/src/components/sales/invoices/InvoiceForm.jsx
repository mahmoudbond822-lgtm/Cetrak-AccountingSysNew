import { useState } from 'react'
import Modal from '../../shared/Modal'
import Button from '../../shared/Button'
import Input from '../../shared/Input'
import ProductSelect from '../../inventory/ProductSelect'
import { salesService } from '../../../services/salesService'

const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }
const selectStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none',
}
const lineHeaderStyle = {
  display: 'grid', gridTemplateColumns: '1.5fr 1.5fr 1fr 1fr 1fr 40px',
  gap: '0.5rem', fontWeight: 600, fontSize: '0.75rem',
  padding: '0.25rem 0', borderBottom: '1px solid var(--border)',
}
const lineRowStyle = {
  display: 'grid', gridTemplateColumns: '1.5fr 1.5fr 1fr 1fr 1fr 40px',
  gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center',
}
const totalsRowStyle = {
  display: 'flex', justifyContent: 'flex-end', gap: '2rem',
  marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)',
  fontSize: '0.875rem', fontWeight: 600,
}
const num = (v) => {
  const n = parseFloat(v)
  return isNaN(n) ? 0 : n
}
const fmt = (v) => Number(v || 0).toFixed(2)

function emptyLine() {
  return { key: crypto.randomUUID?.() ?? Math.random(), product_id: null, description: '', quantity: '1', unit_price: '', tax_rate: '0' }
}

function seededForm(invoice) {
  if (!invoice) {
    return {
      number: '',
      customer_id: '',
      invoice_date: '',
      due_date: '',
      discount: '0',
      notes: '',
      lines: [emptyLine()],
    }
  }
  return {
    number: invoice.number,
    customer_id: invoice.customer_id,
    invoice_date: invoice.invoice_date,
    due_date: invoice.due_date || '',
    discount: invoice.discount,
    notes: invoice.notes || '',
    lines: invoice.lines.map((l) => ({
      key: l.id,
      product_id: l.product_id || null,
      description: l.description,
      quantity: l.quantity,
      unit_price: l.unit_price,
      tax_rate: l.tax_rate,
    })),
  }
}

export default function InvoiceForm({ open, onClose, invoice, customers, nextNumber, onSaved }) {
  const [form, setForm] = useState(seededForm(invoice))
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

  function totals() {
    const subtotal = form.lines.reduce(
      (acc, l) => acc + num(l.quantity || 0) * num(l.unit_price || 0),
      0
    )
    const tax = form.lines.reduce(
      (acc, l) => acc + num(l.quantity || 0) * num(l.unit_price || 0) * num(l.tax_rate || 0) / 100,
      0
    )
    const discount = num(form.discount || 0)
    return { subtotal, tax, total: subtotal - discount + tax }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setFormErrors({})
    const lines = form.lines
      .filter((l) => l.description && num(l.quantity) > 0 && l.unit_price !== '')
      .map((l) => ({
        product_id: l.product_id || null,
        description: l.description,
        quantity: String(num(l.quantity)),
        unit_price: String(num(l.unit_price)),
        tax_rate: String(num(l.tax_rate || 0)),
      }))
    const payload = {
      customer_id: form.customer_id,
      invoice_date: form.invoice_date,
      due_date: form.due_date || null,
      discount: form.discount || '0',
      notes: form.notes || null,
      lines,
    }
    try {
      let saved
      if (invoice) {
        await salesService.updateInvoice(invoice.id, payload)
      } else {
        const res = await salesService.createInvoice(payload)
        saved = res?.data
      }
      onSaved(saved)
      onClose()
    } catch (err) {
      const data = err.response?.data
      if (typeof data === 'object') {
        setFormErrors(data)
      } else {
        setFormErrors({ general: 'Failed to save invoice.' })
      }
    } finally {
      setSaving(false)
    }
  }

  const { subtotal, tax, total } = totals()

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={invoice ? `Edit Invoice ${invoice.number}` : 'New Invoice'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleSubmit} disabled={saving}>
            {saving ? 'Saving...' : invoice ? 'Save Changes' : 'Create Invoice'}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div style={fieldStyle}>
          <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>Customer *</label>
          <select style={selectStyle} name="customer_id" value={form.customer_id} onChange={handleChange} required>
            <option value="">Select customer</option>
            {(customers || []).map((c) => (
              <option key={c.id} value={c.id}>{c.code} – {c.name}</option>
            ))}
          </select>
          {formErrors.customer_id && <span style={{ color: '#F44336', fontSize: '0.75rem' }}>{Array.isArray(formErrors.customer_id) ? formErrors.customer_id[0] : formErrors.customer_id}</span>}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
          {invoice ? (
            <Input label="Invoice Number" value={form.number} readOnly />
          ) : (
            <Input label="Invoice Number (auto-assigned)" value={nextNumber || 'INV-0001'} readOnly />
          )}
          <Input label="Invoice Date" type="date" name="invoice_date" value={form.invoice_date} onChange={handleChange} required />
          <Input label="Due Date" type="date" name="due_date" value={form.due_date} onChange={handleChange} error={formErrors.due_date} />
        </div>

        <div style={{ marginTop: '1rem' }}>
          <div style={lineHeaderStyle}>
            <span>Product</span>
            <span>Description</span>
            <span>Quantity</span>
            <span>Unit Price</span>
            <span>Tax Rate %</span>
            <span />
          </div>
          {form.lines.map((l) => (
            <div key={l.key} style={lineRowStyle}>
              <ProductSelect
                value={l.product_id}
                onChange={(v) => handleLineChange(l.key, 'product_id', v)}
                includeEmpty
              />
              <input
                style={{ padding: '0.4rem 0.6rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}
                placeholder="Item description"
                value={l.description}
                onChange={(e) => handleLineChange(l.key, 'description', e.target.value)}
              />
              <input
                style={{ padding: '0.4rem 0.6rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}
                type="number" min="0" step="any"
                value={l.quantity}
                onChange={(e) => handleLineChange(l.key, 'quantity', e.target.value)}
              />
              <input
                style={{ padding: '0.4rem 0.6rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}
                type="number" min="0" step="any"
                value={l.unit_price}
                onChange={(e) => handleLineChange(l.key, 'unit_price', e.target.value)}
              />
              <input
                style={{ padding: '0.4rem 0.6rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}
                type="number" min="0" max="100" step="any"
                value={l.tax_rate}
                onChange={(e) => handleLineChange(l.key, 'tax_rate', e.target.value)}
              />
              <Button variant="danger" style={{ padding: '0.25rem 0.5rem' }} onClick={() => removeLine(l.key)}>×</Button>
            </div>
          ))}
          <Button variant="secondary" onClick={addLine}>+ Add Line</Button>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: '1rem' }}>
          <div style={{ width: '180px' }}>
            <Input label="Discount" type="number" min="0" step="any" name="discount" value={form.discount} onChange={handleChange} />
          </div>
          <div style={totalsRowStyle}>
            <span>Subtotal: {fmt(subtotal)}</span>
            <span>Tax: {fmt(tax)}</span>
            <span>Total: {fmt(total)}</span>
          </div>
        </div>

        <div style={fieldStyle}>
          <Input label="Notes" name="notes" value={form.notes} onChange={handleChange} />
        </div>
        {formErrors.general && (
          <div style={{ padding: '0.5rem', background: '#FFF3F3', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.8rem' }}>{formErrors.general}</div>
        )}
      </form>
    </Modal>
  )
}