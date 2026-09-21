import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../../lib/cn'
import { color, font, radius, shadow, space, z } from '../../lib/tokens'
import { ToastContext } from './toast-context'

const containerStyle = {
  position: 'fixed',
  top: space[4],
  right: space[4],
  zIndex: z.toast,
  display: 'flex',
  flexDirection: 'column',
  gap: space[2],
  width: '360px',
  maxWidth: 'calc(100vw - 32px)',
  pointerEvents: 'none',
}

const toastBaseStyle = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: space[3],
  padding: `${space[3]} ${space[4]}`,
  background: color.bg.elevated,
  border: `1px solid ${color.border.default}`,
  borderRadius: radius.md,
  boxShadow: shadow.md,
  fontSize: font.size.bodySmall,
  color: color.text.primary,
  pointerEvents: 'auto',
  animation: 'cetrak-toast-in 160ms ease',
}

const toneAccent = {
  success: color.semantic.success,
  error: color.semantic.danger,
  warning: color.semantic.warning,
  info: color.semantic.info,
}

const iconStyle = { flexShrink: 0, marginTop: '1px' }
const contentStyle = { flex: 1, minWidth: 0 }
const closeButtonStyle = {
  flexShrink: 0,
  border: 'none',
  background: 'transparent',
  color: color.text.muted,
  cursor: 'pointer',
  padding: '2px',
  borderRadius: radius.sm,
  display: 'inline-flex',
}

const icons = {
  success: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  ),
  error: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4M12 16h.01" />
    </svg>
  ),
  warning: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  ),
  info: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  ),
}

let toastSeq = 0

/**
 * ToastProvider — mounts the toast viewport. Wrap the app once.
 *
 * `useToast()` returns `{ success, error, warning, info }`, each accepting a message
 * and an optional duration (default 5s). Replaces the 11 blocking `alert()` usages
 * with non-blocking, accessible notifications.
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timers = useRef(new Map())

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
    const timer = timers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
  }, [])

  const show = useCallback((tone, message, duration = 5000) => {
    const id = `toast-${++toastSeq}`
    setToasts((prev) => [...prev, { id, tone, message }])
    if (duration > 0) {
      timers.current.set(id, setTimeout(() => dismiss(id), duration))
    }
    return id
  }, [dismiss])

  const api = useMemo(
    () => ({
      success: (msg, duration) => show('success', msg, duration),
      error: (msg, duration) => show('error', msg, duration),
      warning: (msg, duration) => show('warning', msg, duration),
      info: (msg, duration) => show('info', msg, duration),
      dismiss,
    }),
    [show, dismiss],
  )

  useEffect(() => {
    const map = timers.current
    return () => {
      map.forEach((timer) => clearTimeout(timer))
      map.clear()
    }
  }, [])

  return (
    <ToastContext.Provider value={api}>
      {children}
      {createPortal(
        <div style={containerStyle} aria-live="polite">
          {toasts.map((t) => (
            <div
              key={t.id}
              className={cn('cetrak-toast')}
              style={{
                ...toastBaseStyle,
                borderLeft: `3px solid ${toneAccent[t.tone]}`,
              }}
              role={t.tone === 'error' ? 'alert' : 'status'}
            >
              <span style={{ ...iconStyle, color: toneAccent[t.tone] }}>{icons[t.tone]}</span>
              <div style={contentStyle}>{t.message}</div>
              <button
                type="button"
                style={closeButtonStyle}
                onClick={() => dismiss(t.id)}
                aria-label="Dismiss notification"
                className="cetrak-focus-visible"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  )
}

export default ToastProvider
