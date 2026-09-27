import { useState, useEffect, useCallback } from 'react'
import JournalEntryForm from '../../components/accounting/journal/JournalEntryForm'
import { accountingService } from '../../services/accountingService'
import { useToast } from '../../components/ui'
import {
  Alert, Badge, Button, ConfirmDialog, EmptyState, Input, PageContainer, PageHeader, Pagination, Skeleton,
} from '../../components/ui'
import { color, font, space } from '../../lib/tokens'
import { PAGE_SIZE } from '../../lib/pagination'

const filterStyle = {
  display: 'flex',
  gap: space[3],
  alignItems: 'flex-end',
  marginBottom: space[4],
  flexWrap: 'wrap',
}

const listStyle = {
  border: `1px solid ${color.border.default}`,
  borderRadius: 'var(--radius-md)',
  overflow: 'hidden',
  background: color.bg.surface,
}

const rowStyle = {
  display: 'flex',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: space[3],
  padding: `${space[3]} ${space[4]}`,
  borderBottom: `1px solid ${color.border.subtle}`,
  fontSize: font.size.bodySmall,
}

const refStyle = {
  fontWeight: font.weight.medium,
  color: color.text.primary,
}

const dateStyle = {
  color: color.text.muted,
  fontSize: font.size.caption,
}

const descStyle = {
  flex: 1,
  minWidth: 0,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  color: color.text.secondary,
}

const amountsStyle = {
  textAlign: 'right',
  fontSize: font.size.caption,
  whiteSpace: 'nowrap',
  fontVariantNumeric: 'tabular-nums',
}

export default function JournalPage() {
  const toast = useToast()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [pendingPost, setPendingPost] = useState(null)
  const [posting, setPosting] = useState(false)

  const fetchEntries = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = { page }
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      const { data } = await accountingService.getJournalEntries(params)
      if ((data.results || []).length === 0 && page > 1) {
        const first = await accountingService.getJournalEntries({ ...params, page: 1 })
        setEntries(first.data.results || [])
        setTotal(first.data.count ?? 0)
        setPage(1)
      } else {
        setEntries(data.results || [])
        setTotal(data.count ?? 0)
      }
    } catch {
      setError('Failed to load journal entries.')
    } finally {
      setLoading(false)
    }
  }, [dateFrom, dateTo, page])

  useEffect(() => { fetchEntries() }, [fetchEntries])

  function handleSaved() {
    setShowForm(false)
    fetchEntries()
  }

  function handlePostEntry(entry) {
    setPendingPost(entry)
  }

  async function confirmPost() {
    const entry = pendingPost
    if (!entry) return
    setPosting(true)
    setError('')
    try {
      await accountingService.postJournalEntry(entry.id)
      await fetchEntries()
      toast.success(`Journal entry "${entry.reference}" posted.`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to post journal entry.')
    } finally {
      setPosting(false)
      setPendingPost(null)
    }
  }

  if (showForm) {
    return (
      <PageContainer>
        <PageHeader
          title="New journal entry"
          description="Record a balanced double-entry transaction."
          breadcrumbs={[{ label: 'Accounting' }, { label: 'Journal Entries' }, { label: 'New' }]}
        />
        <JournalEntryForm onSaved={handleSaved} onCancel={() => setShowForm(false)} />
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Journal Entries"
        description="Create and post double-entry transactions."
        breadcrumbs={[{ label: 'Accounting' }, { label: 'Journal Entries' }]}
        primaryAction={
          <Button variant="primary" onClick={() => setShowForm(true)}>New Entry</Button>
        }
      />

      <div style={filterStyle}>
        <Input
          label="From"
          type="date"
          value={dateFrom}
          onChange={(e) => { setDateFrom(e.target.value); setPage(1) }}
          style={{ width: '170px' }}
        />
        <Input
          label="To"
          type="date"
          value={dateTo}
          onChange={(e) => { setDateTo(e.target.value); setPage(1) }}
          style={{ width: '170px' }}
        />
        {(dateFrom || dateTo) && (
          <Button variant="ghost" onClick={() => { setDateFrom(''); setDateTo(''); setPage(1) }}>
            Clear
          </Button>
        )}
      </div>

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: space[2] }} aria-busy="true">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} height="56px" />
          ))}
        </div>
      ) : total === 0 ? (
        <EmptyState
          title="No journal entries yet"
          description="Create your first double-entry transaction to get started."
          action={<Button variant="primary" onClick={() => setShowForm(true)}>New Entry</Button>}
        />
      ) : (
        <div style={listStyle}>
          {entries.map((entry) => (
            <div key={entry.id} style={rowStyle}>
              <div style={{ minWidth: '140px' }}>
                <div style={refStyle}>{entry.reference}</div>
                <div style={dateStyle}>{entry.date}</div>
              </div>
              <div style={descStyle} title={entry.description}>
                {entry.description}
              </div>
              <div style={amountsStyle}>
                <div>Dr {parseFloat(entry.total_debit).toFixed(2)}</div>
                <div>Cr {parseFloat(entry.total_credit).toFixed(2)}</div>
              </div>
              <div style={{ fontSize: font.size.caption, color: color.text.muted, whiteSpace: 'nowrap' }}>
                {entry.line_count} lines
              </div>
              {entry.posted ? (
                <Badge tone="success" size="sm" dot>Posted</Badge>
              ) : (
                <Badge tone="warning" size="sm" dot>Draft</Badge>
              )}
              {!entry.posted && (
                <Button variant="secondary" size="sm" onClick={() => handlePostEntry(entry)}>
                  Post
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      {total > 0 && (
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onPageChange={setPage}
          style={{ marginTop: space[3], justifyContent: 'flex-start' }}
        />
      )}

      <ConfirmDialog
        open={Boolean(pendingPost)}
        title="Post journal entry"
        description={
          pendingPost
            ? `Post journal entry "${pendingPost.reference}"? This will create permanent ledger records and cannot be undone.`
            : ''
        }
        confirmLabel="Post"
        loading={posting}
        onConfirm={confirmPost}
        onCancel={() => setPendingPost(null)}
      />
    </PageContainer>
  )
}
