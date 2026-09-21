/**
 * Tiny className combiner. Avoids pulling in a dependency for a design system
 * that mostly uses inline styles.
 */
export function cn(...args) {
  return args.filter(Boolean).join(' ')
}
