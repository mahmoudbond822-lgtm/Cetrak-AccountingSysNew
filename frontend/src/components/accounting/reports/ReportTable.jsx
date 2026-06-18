const tableStyle = { width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }
const thStyle = {
  textAlign: 'left', padding: '0.625rem 1rem', borderBottom: '2px solid var(--border)',
  fontWeight: 600, color: 'var(--text)', background: '#f9f9f9',
}
const tdStyle = { padding: '0.5rem 1rem', borderBottom: '1px solid var(--border)' }
const numStyle = { ...tdStyle, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }

function renderSection(title, rows, totalField, totalValue) {
  if (!rows || rows.length === 0) return null
  return (
    <table style={tableStyle}>
      <thead>
        <tr>
          <th style={thStyle} colSpan={2}>{title}</th>
          <th style={{ ...thStyle, textAlign: 'right' }}>Amount</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            <td style={tdStyle}>{row.account_name}</td>
            <td style={{ ...tdStyle, color: 'var(--text)', fontSize: '0.8rem' }}>{row.balance || row.account_type || ''}</td>
            <td style={numStyle}>{parseFloat(row.balance || row.debit || 0).toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
      {totalValue && (
        <tfoot>
          <tr style={{ fontWeight: 600, borderTop: '2px solid var(--border)' }}>
            <td style={tdStyle} colSpan={2}>Total {title}</td>
            <td style={numStyle}>{parseFloat(totalValue).toFixed(2)}</td>
          </tr>
        </tfoot>
      )}
    </table>
  )
}

export default function ReportTable({ data }) {
  if (!data) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text)', fontSize: '0.875rem' }}>
        Select a report type and click Generate Report.
      </div>
    )
  }

  const reportType = data.report_type
  const subtitle = reportType === 'balance-sheet'
    ? `As of ${data.as_of || 'N/A'}`
    : `${data.date_from || 'beginning'} to ${data.date_to || 'today'}`

  if (reportType === 'trial-balance') {
    return (
      <div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text)', marginBottom: '1rem' }}>{subtitle}</div>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Account</th>
              <th style={thStyle}>Type</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Debit</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Credit</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i}>
                <td style={tdStyle}>{row.account_name}</td>
                <td style={{ ...tdStyle, color: 'var(--text)', fontSize: '0.8rem' }}>{row.account_type}</td>
                <td style={numStyle}>{parseFloat(row.debit).toFixed(2)}</td>
                <td style={numStyle}>{parseFloat(row.credit).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
          {data.totals && (
            <tfoot>
              <tr style={{ fontWeight: 600, borderTop: '2px solid var(--border)' }}>
                <td style={tdStyle} colSpan={2}>Totals</td>
                <td style={numStyle}>{parseFloat(data.totals.total_debit).toFixed(2)}</td>
                <td style={numStyle}>{parseFloat(data.totals.total_credit).toFixed(2)}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    )
  }

  if (reportType === 'income-statement') {
    return (
      <div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text)', marginBottom: '1rem' }}>{subtitle}</div>
        {renderSection('Revenue', data.revenues, null, data.total_revenue)}
        <div style={{ height: '1rem' }} />
        {renderSection('Expenses', data.expenses, null, data.total_expenses)}
        <div style={{ height: '1rem' }} />
        <div style={{
          padding: '0.75rem 1rem', borderTop: '2px solid var(--border)',
          fontWeight: 600, textAlign: 'right', fontSize: '0.875rem',
        }}>
          Net Income: {parseFloat(data.net_income).toFixed(2)}
        </div>
      </div>
    )
  }

  if (reportType === 'balance-sheet') {
    return (
      <div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text)', marginBottom: '1rem' }}>{subtitle}</div>
        {renderSection('Assets', data.assets, null, data.total_assets)}
        <div style={{ height: '1rem' }} />
        {renderSection('Liabilities', data.liabilities, null, data.total_liabilities)}
        {renderSection('Equity', data.equity, null, data.total_equity)}
        <div style={{ height: '1rem' }} />
        <div style={{
          padding: '0.75rem 1rem', borderTop: '2px solid var(--border)',
          fontWeight: 600, textAlign: 'right', fontSize: '0.875rem',
        }}>
          Total Liabilities &amp; Equity: {parseFloat(data.total_liabilities_and_equity).toFixed(2)}
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text)' }}>
      Unknown report type: {reportType}
    </div>
  )
}
