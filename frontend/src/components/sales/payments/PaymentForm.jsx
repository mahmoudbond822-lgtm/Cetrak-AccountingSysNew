import { useState, useEffect } from 'react'
import Modal from '../../shared/Modal'
import Button from '../../shared/Button'
import Input from '../../shared/Input'
import { accountingService } from '../../../services/accountingService'
import { salesService } from '../../../services/salesService'

const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }
const labelStyle = { fontSize: '0.8rem', fontWeight: 500 }
const selectStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none',
}
const money = (v) => Number(v || 0).toFixed(2)
const METHODS = ['Cash', 'Bank Transfer', 'Card', 'Check']

function seededForm(payment) {
  if (!payment) {
    return {
      number: '',
      invoice_id: '',
      payment_date: '',
      amount: '',
      method: 'Cash',
      cash_account: '',
      reference: '',
      notes: '',
    }
  }
  return {
    number: payment.number,
    invoice_id: payment.invoice_id,
    payment_date: payment.payment_date,
    amount: payment.amount,
    method: payment.method,
    cash_account: payment.cash_account,
    reference: payment.reference || '',
    notes: payment.notes || '',
  }
}

export default function PaymentForm({ open, onClose, payment, invoices, onSaved }) {
  const [form, setForm] = useState(() => seededForm(payment))
  const [accounts, setAccounts] = useState([])
  const [saving, setSaving] = useState(false)
  const [formErrors, setFormErrors] = useState({})

  useEffect(() => {
    if (!open) return
    let cancelled = false
    accountingService.getAccounts()
      .then(({ data }) => {
        if (!cancelled) setAccounts(data.filter((a) => a.type === 'Asset'))
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [open])

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const selectedInvoice = invoices.find((i) => i.id === form.invoice_id)
  const outstanding = selectedInvoice ? Number(selectedInvoice.outstanding_balance || 0) : null
  const amount = Number(form.amount || 0)
  const amountExceeds = outstanding !== null && amount > outstanding

  async function handleSubmit(e) {
    e.preventDefault()
    if (amountExceeds) {
      setFormErrors({ amount: [`Amount exceeds the outstanding balance of ${money(outstanding)}.`] })
      return
    }
    setSaving(true)
    setFormErrors({})
    const payload = {
      number: form.number,
      invoice_id: form.invoice_id,
      payment_date: form.payment_date,
      amount: String(amount),
      method: form.method,
      cash_account: form.cash_account,
      reference: form.reference || null,
      notes: form.notes || null,
    }
    try {
      if (payment) {
        await salesService.updatePayment(payment.id, payload)
      } else {
        await salesService.createPayment(payload)
      }
      onSaved()
      onClose()
    } catch (err) {
      const data = err.response?.data
      if (typeof data === 'object') {
        setFormErrors(data)
      } else {
        setFormErrors({ general: 'Failed to save payment.' })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={payment ? `Edit Payment ${payment.number}` : 'New Payment'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleSubmit} disabled={saving}>
            {saving ? 'Saving...' : payment ? 'Save Changes' : 'Create Payment'}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div style={fieldStyle}>
          <label style={labelStyle}>Invoice *</label>
          <select style={selectStyle} name="invoice_id" value={form.invoice_id} onChange={handleChange} required>
            <option value="">Select posted invoice</option>
            {invoices.map((i) => (
              <option key={i.id} value={i.id}>
                {i.number} – {i.customer_name} (outstanding {money(i.outstanding_balance)})
              </option>
            ))}
          </select>
          {formErrors.invoice_id && <span style={{ color: '#F44336', fontSize: '0.75rem' }}>{Array.isArray(formErrors.invoice_id) ? formErrors.invoice_id[0] : formErrors.invoice_id}</span>}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
          <Input label="Payment Number *" name="number" value={form.number} onChange={handleChange} error={formErrors.number} required />
          <Input label="Payment Date" type="date" name="payment_date" value={form.payment_date} onChange={handleChange} required />
          <Input
            label={`Amount *${outstanding !== null ? ` (outstanding ${money(outstanding)})` : ''}`}
            type="number" min="0" step="any"
            name="amount" value={form.amount} onChange={handleChange}
            error={formErrors.amount} required
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
          <div style={fieldStyle}>
            <label style={labelStyle}>Payment Method *</label>
            <select style={selectStyle} name="method" value={form.method} onChange={handleChange} required>
              {METHODS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div style={fieldStyle}>
            <label style={labelStyle}>Cash/Bank Account *</label>
            <select style={selectStyle} name="cash_account" value={form.cash_account} onChange={handleChange} required>
              <option value="">Select Asset account</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
            {formErrors.cash_account && <span style={{ color: '#F44336', fontSize: '0.75rem' }}>{Array.isArray(formErrors.cash_account) ? formErrors.cash_account[0] : formErrors.cash_account}</span>}
          </div>
          <Input label="Reference" name="reference" value={form.reference} onChange={handleChange} />
        </div>

        <div style={fieldStyle}>
          <Input label="Notes" name="notes" value={form.notes} onChange={handleChange} />
        </div>
        {amountExceeds && (
          <div style={{ padding: '0.5rem', background: '#FFF3F3', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.8rem' }}>
            Amount exceeds the outstanding balance of {money(outstanding)}.
          </div>
        )}
        {formErrors.general && (
          <div style={{ padding: '0.5rem', background: '#FFF3F3', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.8rem' }}>{formErrors.general}</div>
        )}
        {formErrors.detail && (
          <div style={{ padding: '0.5rem', background: '#FFF3F3', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.8rem' }}>{formErrors.detail}</div>
        )}
      </form>
    </Modal>
  )
}