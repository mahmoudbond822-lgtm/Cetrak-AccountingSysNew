import { useState } from 'react'
import Modal from '../../shared/Modal'
import Button from '../../shared/Button'
import Input from '../../shared/Input'
import { accountingService } from '../../../services/accountingService'

const accountTypes = ['Asset', 'Liability', 'Equity', 'Revenue', 'Expense']

const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }
const labelStyle = { fontSize: '0.8rem', fontWeight: 500, color: 'var(--text)' }
const selectStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none',
}
const textareaStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none',
  minHeight: '80px', resize: 'vertical',
}

const emptyForm = { name: '', type: 'Asset', parent_id: '', description: '' }

export default function CreateAccountModal({ open, onClose, account, accounts, onSaved }) {
  const [form, setForm] = useState(emptyForm)
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
      type: form.type,
      parent_id: form.parent_id || null,
      description: form.description || null,
    }
    try {
      if (account) {
        await accountingService.updateAccount(account.id, payload)
      } else {
        await accountingService.createAccount(payload)
      }
      onSaved()
      onClose()
    } catch (err) {
      const data = err.response?.data
      if (typeof data === 'object') {
        setFormErrors(data)
      } else {
        setFormErrors({ general: 'Failed to save account.' })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={account ? 'Edit Account' : 'Create Account'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleSubmit} disabled={saving}>
            {saving ? 'Saving...' : account ? 'Update' : 'Create'}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div style={fieldStyle}>
          <label style={labelStyle}>Account Name *</label>
          <Input name="name" value={form.name} onChange={handleChange} error={formErrors.name} required />
        </div>
        <div style={fieldStyle}>
          <label style={labelStyle}>Type *</label>
          <select style={selectStyle} name="type" value={form.type} onChange={handleChange}>
            {accountTypes.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div style={fieldStyle}>
          <label style={labelStyle}>Parent Account</label>
          <select style={selectStyle} name="parent_id" value={form.parent_id} onChange={handleChange}>
            <option value="">None (Root Account)</option>
            {(accounts || []).map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <div style={fieldStyle}>
          <label style={labelStyle}>Description</label>
          <textarea style={textareaStyle} name="description" value={form.description} onChange={handleChange} />
        </div>
        {formErrors.general && (
          <div style={{ padding: '0.5rem', background: '#FFF3F3', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.8rem' }}>{formErrors.general}</div>
        )}
      </form>
    </Modal>
  )
}
