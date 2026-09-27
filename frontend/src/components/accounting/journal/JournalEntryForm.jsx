import { useState, useEffect } from 'react'
import JournalLineRow from './JournalLineRow'
import { Alert } from '../../ui'
import { accountingService } from '../../../services/accountingService'

const formStyle = { maxWidth: '720px', margin: '0 auto' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600, marginBottom: '1.5rem' }
const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }
const labelStyle = { fontSize: '0.8rem', fontWeight: 500, color: 'var(--text)' }
const btnPrimary = {
  cursor: 'pointer', background: 'var(--brand)', color: 'var(--brand-foreground)',
  border: 'none', borderRadius: '6px', padding: '0.5rem 1rem',
  fontSize: '0.875rem', fontWeight: 500,
}
const btnDisabled = { ...btnPrimary, opacity: 0.5, cursor: 'not-allowed' }
const btnSecondary = {
  cursor: 'pointer', background: 'transparent', color: 'var(--text)',
  border: '1px solid var(--border)', borderRadius: '6px', padding: '0.5rem 1rem',
  fontSize: '0.875rem',
}
const balanceBarStyle = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1rem',
  fontSize: '0.875rem', fontWeight: 500,
}

function createEmptyLine() {
  return { id: Date.now(), account_id: '', debit: '', credit: '' }
}

// Money is compared in integer minor units at the backend's precision
// (NUMERIC(19,4)) instead of binary floats, so the balance gate is exact
// rather than tolerance-based (AUD-030 / N1).
const MONEY_UNITS = 10000

function toMoneyUnits(value) {
  return Math.round((parseFloat(value) || 0) * MONEY_UNITS)
}

function fromMoneyUnits(units) {
  return units / MONEY_UNITS
}

export default function JournalEntryForm({ onSaved, onCancel }) {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [description, setDescription] = useState('')
  const [reference, setReference] = useState('')
  const [lines, setLines] = useState([createEmptyLine(), createEmptyLine()])
  const [saving, setSaving] = useState(false)
  const [posting, setPosting] = useState(false)
  const [createdDraft, setCreatedDraft] = useState(null)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  useEffect(() => {
    accountingService.getNextJournalReference()
      .then(({ data }) => setReference(data.reference || ''))
      .catch(() => setReference(''))
  }, [])

  const totals = lines.reduce((acc, line) => ({
    debit: acc.debit + toMoneyUnits(line.debit),
    credit: acc.credit + toMoneyUnits(line.credit),
  }), { debit: 0, credit: 0 })

  const balanced = totals.debit === totals.credit
  const hasEmptyAccounts = lines.some((l) => !l.account_id)
  const hasEnoughLines = lines.length >= 2
  const canSubmit = balanced && !hasEmptyAccounts && hasEnoughLines && !saving

  function handleLineChange(index, updatedLine) {
    setLines((prev) => prev.map((l, i) => i === index ? updatedLine : l))
  }

  function handleAddLine() {
    setLines((prev) => [...prev, createEmptyLine()])
  }

  function handleRemoveLine(index) {
    if (lines.length <= 2) return
    setLines((prev) => prev.filter((_, i) => i !== index))
  }

  async function handleSaveDraft() {
    setSaving(true)
    setError('')
    setFieldErrors({})
    const payload = {
      date,
      description,
      lines: lines.map((l) => ({
        account_id: l.account_id,
        debit: fromMoneyUnits(toMoneyUnits(l.debit)),
        credit: fromMoneyUnits(toMoneyUnits(l.credit)),
      })),
    }
    try {
      const { data } = await accountingService.createJournalEntry(payload)
      setCreatedDraft(data)
    } catch (err) {
      const data = err.response?.data
      if (typeof data === 'object') {
        setFieldErrors(data)
        const msgs = Object.values(data).flat().join(' ')
        setError(msgs || 'Failed to save journal entry.')
      } else {
        setError('Failed to save journal entry.')
      }
    } finally {
      setSaving(false)
    }
  }

  async function handlePostDraft() {
    setPosting(true)
    setError('')
    try {
      await accountingService.postJournalEntry(createdDraft.id)
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to post journal entry.')
      setPosting(false)
    }
  }

  const hasUnsavedChanges = date !== new Date().toISOString().split('T')[0] || description || lines.some(l => l.account_id || l.debit || l.credit)

  useEffect(() => {
    function handleBeforeUnload(e) {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])

  return (
    <div style={formStyle}>
      <h1 style={titleStyle}>New Journal Entry</h1>

      {error && (
        <Alert tone="error" style={{ marginBottom: '1rem' }}>{error}</Alert>
      )}

      {createdDraft ? (
        <Alert tone="success" title={`Draft saved (${createdDraft.reference})`} style={{ marginBottom: '1rem' }}>
          This entry is not yet financially effective. Post it to include it
          in the ledger and financial reports.
        </Alert>
      ) : (
        <>
          <div style={fieldStyle}>
            <label style={labelStyle} htmlFor="je-date">Date *</label>
            <input className="cetrak-input" id="je-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </div>
          <div style={fieldStyle}>
            <label style={labelStyle} htmlFor="je-reference">Reference</label>
            <input className="cetrak-input" id="je-reference" style={{ background: 'var(--bg-hover)' }} value={reference} readOnly placeholder="JE-2026-0001" title="Assigned automatically on save" />
          </div>
        </>
      )}

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="je-description">Description *</label>
        <textarea className="cetrak-input" id="je-description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Transaction description" required />
      </div>

      <div style={{
        ...balanceBarStyle,
        background: totals.debit > 0 || totals.credit > 0 ? (balanced ? 'var(--success-soft)' : 'var(--danger-soft)') : 'var(--bg-hover)',
        border: `1px solid ${totals.debit > 0 || totals.credit > 0 ? (balanced ? 'var(--success)' : 'var(--danger)') : 'var(--border)'}`,
      }}>
        <span>Total Debit: <strong>{fromMoneyUnits(totals.debit).toFixed(4)}</strong></span>
        <span>Total Credit: <strong>{fromMoneyUnits(totals.credit).toFixed(4)}</strong></span>
        <span style={{ color: totals.debit > 0 || totals.credit > 0 ? (balanced ? 'var(--success)' : 'var(--danger)') : 'var(--text-muted)' }}>
          {totals.debit === 0 && totals.credit === 0 ? 'Enter amounts' : balanced ? '✓ Balanced' : '✗ Imbalanced'}
        </span>
      </div>

      <div style={{ marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Journal Lines</span>
        <button type="button" style={btnSecondary} onClick={handleAddLine} disabled={Boolean(createdDraft)}>+ Add Line</button>
      </div>

      <div style={{ marginBottom: '1rem' }}>
        {lines.map((line, i) => (
          <JournalLineRow
            key={line.id}
            line={line}
            index={i}
            onChange={handleLineChange}
            onRemove={handleRemoveLine}
            disabled={saving || Boolean(createdDraft)}
          />
        ))}
      </div>

      {fieldErrors.non_field_errors && (
        <Alert tone="error" style={{ marginBottom: '1rem' }}>{fieldErrors.non_field_errors.join(' ')}</Alert>
      )}

      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
        {createdDraft ? (
          <>
            <button type="button" style={btnSecondary} onClick={onCancel}>
              Done
            </button>
            <button
              type="button"
              style={posting ? btnDisabled : btnPrimary}
              disabled={posting}
              onClick={handlePostDraft}
            >
              {posting ? 'Posting...' : 'Post Entry'}
            </button>
          </>
        ) : (
          <>
            <button type="button" style={btnSecondary} onClick={onCancel}>Cancel</button>
            <button
              type="button"
              style={canSubmit ? btnPrimary : btnDisabled}
              disabled={!canSubmit}
              onClick={handleSaveDraft}
            >
              {saving ? 'Saving...' : 'Save Draft'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
