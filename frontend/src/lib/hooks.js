import { useSyncExternalStore } from 'react'

/**
 * useMediaQuery — reactive CSS media query for responsive behavior.
 *
 * Implemented with useSyncExternalStore (no setState-in-effect), so it is
 * concurrent-safe and lint-clean.
 */
export function useMediaQuery(query) {
  const subscribe = (callback) => {
    if (typeof window === 'undefined' || !window.matchMedia) return () => {}
    const mql = window.matchMedia(query)
    mql.addEventListener('change', callback)
    return () => mql.removeEventListener('change', callback)
  }

  const getSnapshot = () => {
    if (typeof window === 'undefined' || !window.matchMedia) return false
    return window.matchMedia(query).matches
  }

  const getServerSnapshot = () => false

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}

export const LG_BREAKPOINT = '(min-width: 1024px)'
