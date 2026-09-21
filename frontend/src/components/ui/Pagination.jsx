import { color, font, radius, space } from '../../lib/tokens'
import { cn } from '../../lib/cn'

const navStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[1],
  fontSize: font.size.bodySmall,
  color: color.text.secondary,
}

const buttonStyle = {
  minWidth: '32px',
  height: '32px',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  border: `1px solid ${color.border.default}`,
  background: color.bg.surface,
  color: color.text.secondary,
  borderRadius: radius.sm,
  cursor: 'pointer',
  fontSize: font.size.bodySmall,
  padding: `0 ${space[2]}`,
}

const activeButtonStyle = {
  background: color.brand.primary,
  color: color.brand.foreground,
  borderColor: color.brand.primary,
  fontWeight: font.weight.semibold,
}

const disabledStyle = { opacity: 0.4, cursor: 'not-allowed' }

const summaryStyle = { marginLeft: space[3], color: color.text.muted, fontSize: font.size.caption }

function pageRange(current, totalPages) {
  const delta = 1
  const range = []
  for (let i = Math.max(2, current - delta); i <= Math.min(totalPages - 1, current + delta); i++) {
    range.push(i)
  }
  const pages = [1, ...range, totalPages].filter((v, i, arr) => arr.indexOf(v) === i && v >= 1 && v <= totalPages)
  return pages
}

/**
 * Pagination — standard table paging control.
 *
 * Present for adoption as the API grows; only wired where a page already paginates.
 */
export default function Pagination({ page, pageSize, total, onPageChange, className, style }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  if (totalPages <= 1) return null

  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)
  const pages = pageRange(page, totalPages)

  return (
    <nav
      className={cn(className)}
      style={{ ...navStyle, ...style }}
      aria-label="Pagination"
    >
      <button
        type="button"
        style={{ ...buttonStyle, ...(page === 1 ? disabledStyle : null) }}
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        aria-label="Previous page"
      >
        ‹
      </button>
      {pages.map((p) => (
        <button
          key={p}
          type="button"
          style={{
            ...buttonStyle,
            ...(p === page ? activeButtonStyle : null),
          }}
          onClick={() => onPageChange(p)}
          aria-current={p === page ? 'page' : undefined}
        >
          {p}
        </button>
      ))}
      <button
        type="button"
        style={{ ...buttonStyle, ...(page === totalPages ? disabledStyle : null) }}
        onClick={() => onPageChange(page + 1)}
        disabled={page === totalPages}
        aria-label="Next page"
      >
        ›
      </button>
      <span style={summaryStyle} aria-live="polite">
        {from}–{to} of {total}
      </span>
    </nav>
  )
}
