import { color, font, space } from '../../../lib/tokens'
import { AccountingTypeBadge } from '../../ui'

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: font.size.bodySmall,
}

const thStyle = {
  textAlign: 'left',
  padding: `${space[3]} ${space[4]}`,
  borderBottom: `1px solid ${color.border.default}`,
  fontWeight: font.weight.semibold,
  color: color.text.muted,
  background: color.bg.hover,
  fontSize: font.size.caption,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

const tdStyle = {
  padding: `${space[2]} ${space[4]}`,
  borderBottom: `1px solid ${color.border.subtle}`,
  color: color.text.primary,
}

const numStyle = {
  ...tdStyle,
  textAlign: 'right',
  fontVariantNumeric: 'tabular-nums',
}

const sectionTitleStyle = {
  fontSize: font.size.cardTitle,
  fontWeight: font.weight.semibold,
  color: color.text.primary,
  margin: `${space[5]} 0 ${space[2]}`,
}

const totalRowStyle = {
  padding: `${space[3]} ${space[4]}`,
  borderTop: `1px solid ${color.border.strong}`,
  fontWeight: font.weight.semibold,
  textAlign: 'right',
  color: color.text.primary,
}

const subtitleStyle = {
  fontSize: font.size.caption,
  color: color.text.muted,
  marginBottom: space[3],
}

function renderSection(title, rows, totalValue) {
  if (!rows || rows.length === 0) return null
  return (
    <div>
      <div style={sectionTitleStyle}>{title}</div>
      <div className="cetrak-table-scroll">
        <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>Account</th>
            <th style={thStyle}>Type</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>Amount</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              <td style={tdStyle}>{row.account_name}</td>
              <td style={tdStyle}>
                {row.account_type ? <AccountingTypeBadge type={row.account_type} size="sm" /> : '—'}
              </td>
              <td style={numStyle}>{parseFloat(row.balance || row.debit || 0).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
        {totalValue && (
          <tfoot>
            <tr>
              <td style={totalRowStyle} colSpan={2}>Total {title}</td>
              <td style={totalRowStyle}>{parseFloat(totalValue).toFixed(2)}</td>
            </tr>
          </tfoot>
        )}
      </table>
      </div>
    </div>
  )
}

export default function ReportTable({ data }) {
  if (!data) {
    return (
      <div style={{ padding: space[8], textAlign: 'center', color: color.text.muted, fontSize: font.size.bodySmall }}>
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
        <div style={subtitleStyle}>{subtitle}</div>
        <div className="cetrak-table-scroll">
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
                  <td style={tdStyle}>
                    {row.account_type ? <AccountingTypeBadge type={row.account_type} size="sm" /> : '—'}
                  </td>
                  <td style={numStyle}>{parseFloat(row.debit).toFixed(2)}</td>
                  <td style={numStyle}>{parseFloat(row.credit).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
            {data.totals && (
              <tfoot>
                <tr>
                  <td style={totalRowStyle} colSpan={2}>Totals</td>
                  <td style={totalRowStyle}>{parseFloat(data.totals.total_debit).toFixed(2)}</td>
                  <td style={totalRowStyle}>{parseFloat(data.totals.total_credit).toFixed(2)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>
    )
  }

  if (reportType === 'income-statement') {
    return (
      <div>
        <div style={subtitleStyle}>{subtitle}</div>
        {renderSection('Revenue', data.revenues, data.total_revenue)}
        {renderSection('Expenses', data.expenses, data.total_expenses)}
        <div style={totalRowStyle}>
          Net Income: {parseFloat(data.net_income).toFixed(2)}
        </div>
      </div>
    )
  }

  if (reportType === 'balance-sheet') {
    return (
      <div>
        <div style={subtitleStyle}>{subtitle}</div>
        {renderSection('Assets', data.assets, data.total_assets)}
        {renderSection('Liabilities', data.liabilities, data.total_liabilities)}
        {renderSection('Equity', data.equity, data.total_equity)}
        <div style={totalRowStyle}>
          Total Liabilities &amp; Equity: {parseFloat(data.total_liabilities_and_equity).toFixed(2)}
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: space[8], textAlign: 'center', color: color.text.muted }}>
      Unknown report type: {reportType}
    </div>
  )
}
