import { cn } from '../../lib/cn'

/**
 * Skeleton — loading placeholder with a subtle shimmer.
 *
 * Render a single bar or `count` stacked rows via `rows` (which returns a fragment).
 */
export default function Skeleton({
  width = '100%',
  height = '14px',
  count = 1,
  radius = 'var(--radius-sm)',
  className,
  style,
}) {
  if (count > 1) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }} aria-hidden="true">
        {Array.from({ length: count }).map((_, i) => (
          <Skeleton
            key={i}
            width={width}
            height={height}
            radius={radius}
            className={className}
            style={style}
          />
        ))}
      </div>
    )
  }

  return (
    <span
      className={cn('cetrak-skeleton', className)}
      style={{ width, height, borderRadius: radius, ...style }}
      aria-hidden="true"
    />
  )
}

/**
 * SkeletonTable — table-shaped loading state (header + N rows).
 */
export function SkeletonTable({ rows = 5, columns = 4 }) {
  return (
    <div aria-hidden="true" style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} height="12px" style={{ flex: 1 }} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} style={{ display: 'flex', gap: 'var(--space-4)' }}>
          {Array.from({ length: columns }).map((_, c) => (
            <Skeleton key={c} height="16px" style={{ flex: 1 }} />
          ))}
        </div>
      ))}
    </div>
  )
}
