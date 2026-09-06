import { useState, useEffect } from 'react'
import JournalLineRow from './JournalLineRow'
import { accountingService } from '../../../services/accountingService'

const formStyle = { maxWidth: '720px', margin: '0 auto' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600, marginBottom: '1.5rem' }
const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }
const labelStyle = { fontSize: '0.8rem', fontWeight: 500, color: 'var(--text)' }
const inputStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none',
}
const btnPrimary = {
  cursor: 'pointer', background: 'var(--accent)', color: '#fff',
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

  const totals = lines.reduce((acc, line) => ({
    debit: acc.debit + (parseFloat(line.debit) || 0),
    credit: acc.credit + (parseFloat(line.credit) || 0),
  }), { debit: 0, credit: 0 })

  const balanced = Math.abs(totals.debit - totals.credit) < 0.001
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
      reference,
      lines: lines.map((l) => ({
        account_id: l.account_id,
        debit: parseFloat(l.debit) || 0,
        credit: parseFloat(l.credit) || 0,
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

  const hasUnsavedChanges = date !== new Date().toISOString().split('T')[0] || description || reference || lines.some(l => l.account_id || l.debit || l.credit)

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
        <div style={{ padding: '0.75rem 1rem', background: '#FFF3F3', border: '1px solid #F44336', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.875rem' }}>
          {error}
        </div>
      )}

      {createdDraft ? (
        <div style={{
          padding: '1rem', background: '#F0FFF0', border: '1px solid #4CAF50',
          borderRadius: '8px', marginBottom: '1rem', fontSize: '0.875rem',
        }}>
          <div style={{ fontWeight: 500, marginBottom: '0.375rem' }}>
            Draft saved ({createdDraft.reference})
          </div>
          <div style={{ color: 'var(--text)' }}>
            This entry is not yet financially effective. Post it to include it
            in the ledger and financial reports.
          </div>
        </div>
      ) : (
        <>
          <div style={fieldStyle}>
            <label style={labelStyle}>Date *</label>
            <input style={inputStyle} type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </div>
          <div style={fieldStyle}>
            <label style={labelStyle}>Reference *</label>
            <input style={inputStyle} value={reference} onChange={(e) => setReference(e.target.value)} placeholder="JE-2026-001" required />
          </div>
        </>
      )}

      <div style={fieldStyle}>
        <label style={labelStyle}>Description *</label>
        <textarea style={{ ...inputStyle, minHeight: '60px', resize: 'vertical' }} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Transaction description" required />
      </div>

      <div style={{
        ...balanceBarStyle,
        background: totals.debit > 0 || totals.credit > 0 ? (balanced ? '#F0FFF0' : '#FFF3F3') : '#f9f9f9',
        border: `1px solid ${totals.debit > 0 || totals.credit > 0 ? (balanced ? '#4CAF50' : '#F44336') : 'var(--border)'}`,
      }}>
        <span>Total Debit: <strong>{totals.debit.toFixed(4)}</strong></span>
        <span>Total Credit: <strong>{totals.credit.toFixed(4)}</strong></span>
        <span style={{ color: totals.debit > 0 || totals.credit > 0 ? (balanced ? '#4CAF50' : '#F44336') : 'var(--text)' }}>
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
        <div style={{ padding: '0.5rem', background: '#FFF3F3', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.8rem' }}>
          {fieldErrors.non_field_errors.join(' ')}
        </div>
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
