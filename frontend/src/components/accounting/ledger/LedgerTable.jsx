const tableStyle = { width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }
const thStyle = {
  textAlign: 'left', padding: '0.625rem 1rem', borderBottom: '2px solid var(--border)',
  fontWeight: 600, color: 'var(--text)', background: '#f9f9f9', whiteSpace: 'nowrap',
}
const tdStyle = { padding: '0.5rem 1rem', borderBottom: '1px solid var(--border)' }
const numStyle = { ...tdStyle, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }

export default function LedgerTable({ entries, totals }) {
  if (!entries || entries.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text)', fontSize: '0.875rem' }}>
        No transactions found for this account.
      </div>
    )
  }

  return (
    <table style={tableStyle}>
      <thead>
        <tr>
          <th style={thStyle}>Date</th>
          <th style={thStyle}>Reference</th>
          <th style={thStyle}>Description</th>
          <th style={{ ...thStyle, textAlign: 'right' }}>Debit</th>
          <th style={{ ...thStyle, textAlign: 'right' }}>Credit</th>
          <th style={{ ...thStyle, textAlign: 'right' }}>Running Balance</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((row, i) => (
          <tr key={i}>
            <td style={tdStyle}>{row.date}</td>
            <td style={tdStyle}>{row.reference}</td>
            <td style={tdStyle}>{row.description}</td>
            <td style={numStyle}>{parseFloat(row.debit).toFixed(2)}</td>
            <td style={numStyle}>{parseFloat(row.credit).toFixed(2)}</td>
            <td style={numStyle}>{parseFloat(row.running_balance).toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
      {totals && (
        <tfoot>
          <tr style={{ fontWeight: 600, borderTop: '2px solid var(--border)' }}>
            <td colSpan={3} style={{ ...tdStyle, textAlign: 'right' }}>Totals</td>
            <td style={numStyle}>{parseFloat(totals.total_debit).toFixed(2)}</td>
            <td style={numStyle}>{parseFloat(totals.total_credit).toFixed(2)}</td>
            <td style={numStyle}>{parseFloat(totals.closing_balance).toFixed(2)}</td>
          </tr>
        </tfoot>
      )}
    </table>
  )
}
