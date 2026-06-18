const tableStyle = { width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }
const thStyle = {
  textAlign: 'left', padding: '0.625rem 1rem', borderBottom: '2px solid var(--border)',
  fontWeight: 600, color: 'var(--text)', background: '#f9f9f9',
}
const tdStyle = { padding: '0.5rem 1rem', borderBottom: '1px solid var(--border)' }
const emptyStyle = {
  padding: '2rem', textAlign: 'center', color: 'var(--text)', fontSize: '0.875rem',
}

export default function Table({ columns, data, footer, emptyMessage = 'No data available.' }) {
  if (!data || data.length === 0) {
    return <div style={emptyStyle}>{emptyMessage}</div>
  }

  return (
    <table style={tableStyle}>
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={col.key} style={{ ...thStyle, ...(col.align ? { textAlign: col.align } : {}) }}>
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr key={row.id ?? i}>
            {columns.map((col) => (
              <td key={col.key} style={{ ...tdStyle, ...(col.align ? { textAlign: col.align } : {}) }}>
                {col.render ? col.render(row) : row[col.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
      {footer && (
        <tfoot>
          <tr style={{ fontWeight: 600, borderTop: '2px solid var(--border)' }}>
            {columns.map((col) => (
              <td key={col.key} style={{ ...tdStyle, ...(col.align ? { textAlign: col.align } : {}) }}>
                {col.footer ? col.footer : ''}
              </td>
            ))}
          </tr>
        </tfoot>
      )}
    </table>
  )
}
