import { useState, useEffect } from 'react'
import { Modal, Button, Input, Select, Alert } from '../../ui'
import { accountingService } from '../../../services/accountingService'
import { purchasesService } from '../../../services/purchasesService'

const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }
const money = (v) => Number(v || 0).toFixed(2)
const METHODS = ['Cash', 'Bank Transfer', 'Card', 'Check']

function seededForm(payment) {
  if (!payment) {
    return {
      number: '',
      purchase_invoice_id: '',
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
    purchase_invoice_id: payment.purchase_invoice_id,
    payment_date: payment.payment_date,
    amount: payment.amount,
    method: payment.method,
    cash_account: payment.cash_account,
    reference: payment.reference || '',
    notes: payment.notes || '',
  }
}

export default function PurchasePaymentForm({ open, onClose, payment, invoices, onSaved }) {
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

  const selectedInvoice = invoices.find((i) => i.id === form.purchase_invoice_id)
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
      purchase_invoice_id: form.purchase_invoice_id,
      payment_date: form.payment_date,
      amount: String(amount),
      method: form.method,
      cash_account: form.cash_account,
      reference: form.reference || null,
      notes: form.notes || null,
    }
    try {
      if (payment) {
        await purchasesService.updatePayment(payment.id, payload)
      } else {
        await purchasesService.createPayment(payload)
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
        <Select
          label="Purchase Invoice *"
          name="purchase_invoice_id"
          value={form.purchase_invoice_id}
          onChange={handleChange}
          error={formErrors.purchase_invoice_id ? (Array.isArray(formErrors.purchase_invoice_id) ? formErrors.purchase_invoice_id[0] : formErrors.purchase_invoice_id) : undefined}
          required
          style={{ marginBottom: '1rem' }}
        >
          <option value="">Select posted invoice</option>
          {invoices.map((i) => (
            <option key={i.id} value={i.id}>
              {i.number} – {i.vendor_name} (outstanding {money(i.outstanding_balance)})
            </option>
          ))}
        </Select>

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
          <Select label="Payment Method *" name="method" value={form.method} onChange={handleChange} required>
            {METHODS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </Select>
          <Select
            label="Cash/Bank Account *"
            name="cash_account"
            value={form.cash_account}
            onChange={handleChange}
            error={formErrors.cash_account ? (Array.isArray(formErrors.cash_account) ? formErrors.cash_account[0] : formErrors.cash_account) : undefined}
            required
          >
            <option value="">Select Asset account</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </Select>
          <Input label="Reference" name="reference" value={form.reference} onChange={handleChange} />
        </div>

        <div style={fieldStyle}>
          <Input label="Notes" name="notes" value={form.notes} onChange={handleChange} />
        </div>
        {amountExceeds && (
          <Alert tone="error" style={{ marginBottom: '1rem' }}>
            Amount exceeds the outstanding balance of {money(outstanding)}.
          </Alert>
        )}
        {formErrors.general && (
          <Alert tone="error" style={{ marginBottom: '1rem' }}>{formErrors.general}</Alert>
        )}
        {formErrors.detail && (
          <Alert tone="error" style={{ marginBottom: '1rem' }}>{formErrors.detail}</Alert>
        )}
      </form>
    </Modal>
  )
}