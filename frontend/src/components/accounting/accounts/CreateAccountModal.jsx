import { useState } from 'react'
import { accountingService } from '../../../services/accountingService'
import { Alert, Button, FormField, Modal, Select, Textarea } from '../../ui'
import { space } from '../../../lib/tokens'

const accountTypes = ['Asset', 'Liability', 'Equity', 'Revenue', 'Expense']

const formStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: space[4],
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
      title={account ? 'Edit account' : 'Create account'}
      description={
        account
          ? 'Update the account details.'
          : 'Add a new account to your chart of accounts.'
      }
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={saving}>
            {account ? 'Update' : 'Create'}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} style={formStyle}>
        <FormField label="Account name" required>
          {({ id, ...a11y }) => (
            <input
              id={id}
              name="name"
              className="cetrak-input"
              value={form.name}
              onChange={handleChange}
              required
              {...a11y}
            />
          )}
        </FormField>

        <Select
          label="Type"
          name="type"
          value={form.type}
          onChange={handleChange}
          error={Array.isArray(formErrors.type) ? formErrors.type[0] : formErrors.type}
          required
        >
          {accountTypes.map((t) => <option key={t} value={t}>{t}</option>)}
        </Select>

        <Select
          label="Parent account"
          name="parent_id"
          value={form.parent_id}
          onChange={handleChange}
          helperText="Leave empty for a root account."
        >
          <option value="">None (root account)</option>
          {(accounts || []).map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </Select>

        <Textarea
          label="Description"
          name="description"
          value={form.description}
          onChange={handleChange}
          rows={3}
        />

        {formErrors.general && (
          <Alert tone="error">{formErrors.general}</Alert>
        )}
      </form>
    </Modal>
  )
}
