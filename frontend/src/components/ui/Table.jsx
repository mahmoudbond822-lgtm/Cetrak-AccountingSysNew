import { cn } from '../../lib/cn'
import { color, font, space } from '../../lib/tokens'
import { SkeletonTable } from './Skeleton'
import EmptyState from './EmptyState'

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: font.size.bodySmall,
}

const thStyle = {
  position: 'sticky',
  top: 0,
  zIndex: 1,
  textAlign: 'left',
  fontSize: font.size.caption,
  fontWeight: font.weight.semibold,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  color: color.text.muted,
  background: color.bg.hover,
  borderBottom: `1px solid ${color.border.default}`,
  padding: `${space[3]} ${space[4]}`,
  whiteSpace: 'nowrap',
}

const tdStyle = {
  padding: `${space[3]} ${space[4]}`,
  borderBottom: `1px solid ${color.border.subtle}`,
  color: color.text.primary,
  verticalAlign: 'middle',
}

const numericStyle = {
  textAlign: 'right',
  fontVariantNumeric: 'tabular-nums',
}

const actionsStyle = {
  textAlign: 'right',
  width: '1%',
  whiteSpace: 'nowrap',
}

const rowHoverStyle = {
  transition: 'background-color 120ms ease',
}

/**
 * Table — standardized data table for the whole product.
 *
 * Supports: sticky header, hover rows, numeric right-alignment via `align: 'right'`
 * or `numeric: true`, an actions column, responsive horizontal scroll, built-in
 * loading (skeleton), built-in empty state, and an optional footer row.
 *
 * `columns: [{ key, label, align, numeric, render, width, footer }]`
 */
export default function Table({
  columns,
  data,
  loading = false,
  emptyTitle = 'Nothing here yet',
  emptyDescription,
  emptyAction,
  rowKey = 'id',
  onRowClick,
  footer = false,
  className,
  style,
}) {
  if (loading) {
    return (
      <div className={cn('cetrak-table-scroll cetrak-scroll', className)} style={style}>
        <SkeletonTable rows={5} columns={Math.max(columns?.length || 4, 3)} />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className={className} style={style}>
        <EmptyState
          title={emptyTitle}
          description={emptyDescription}
          action={emptyAction}
        />
      </div>
    )
  }

  return (
    <div className={cn('cetrak-table-scroll cetrak-scroll', className)} style={style}>
      <table style={{ ...tableStyle, ...style }} className="cetrak-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                style={{
                  ...thStyle,
                  ...(col.align === 'right' || col.numeric ? numericStyle : null),
                  ...(col.width ? { width: col.width } : null),
                }}
                scope="col"
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={typeof rowKey === 'function' ? rowKey(row) : (row[rowKey] ?? i)}
              style={rowHoverStyle}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={
                onRowClick
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onRowClick(row)
                      }
                    }
                  : undefined
              }
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  style={{
                    ...tdStyle,
                    ...(col.align === 'right' || col.numeric ? numericStyle : null),
                    ...(col.isActions ? actionsStyle : null),
                    ...(col.width ? { width: col.width } : null),
                  }}
                >
                  {col.render ? col.render(row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        {footer && (
          <tfoot>
            <tr>
              {columns.map((col) => (
                <td
                  key={col.key}
                  style={{
                    ...tdStyle,
                    fontWeight: font.weight.semibold,
                    borderTop: `1px solid ${color.border.strong}`,
                    background: color.bg.hover,
                    ...(col.align === 'right' || col.numeric ? numericStyle : null),
                  }}
                >
                  {col.footer ? col.footer() : ''}
                </td>
              ))}
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  )
}
