import { createContext, useContext } from 'react'

/**
 * Toast context. Kept in its own module so that the Toast component file only
 * exports components (required by react-refresh/fast-refresh).
 */
export const ToastContext = createContext(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return ctx
}
