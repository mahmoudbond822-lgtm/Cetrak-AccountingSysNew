import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../../lib/cn'
import { color, shadow, z } from '../../lib/tokens'

const overlayStyle = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(9, 10, 14, 0.55)',
  zIndex: z.drawer,
  display: 'flex',
  animation: 'cetrak-fade 140ms ease',
}

const panelBaseStyle = {
  background: color.bg.surface,
  height: '100%',
  width: 'var(--sidebar-width)',
  maxWidth: '85vw',
  boxShadow: shadow.lg,
  display: 'flex',
  flexDirection: 'column',
  overflowY: 'auto',
}

/**
 * Drawer — side panel. Used for mobile navigation and slide-over forms.
 *
 * Same a11y contract as Modal (Escape, overlay click, focus trap, scroll lock).
 */
export default function Drawer({
  open,
  onClose,
  side = 'right',
  width,
  children,
  className,
  style,
}) {
  const panelRef = useRef(null)
  const [panelId] = useState(() => `cetrak-drawer-${Math.random().toString(36).slice(2, 9)}`)

  useEffect(() => {
    if (!open) return undefined

    const previouslyFocused = document.activeElement
    const panel = panelRef.current
    const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key !== 'Tab' || !panel) return
      const focusable = Array.from(panel.querySelectorAll(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null,
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    panel?.querySelector(FOCUSABLE)?.focus?.()

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
      previouslyFocused?.focus?.()
    }
  }, [open, onClose])

  if (!open) return null

  const isRight = side === 'right'

  return createPortal(
    <div
      className="cetrak-overlay"
      style={overlayStyle}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      role="presentation"
    >
      <div
        ref={panelRef}
        id={panelId}
        className={cn('cetrak-drawer', className)}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        style={{
          ...panelBaseStyle,
          width: width || panelBaseStyle.width,
          ...(isRight ? { marginLeft: 'auto' } : { marginRight: 'auto' }),
          animation: `cetrak-drawer-${side} 180ms ease`,
          ...style,
        }}
      >
        {children}
      </div>
    </div>,
    document.body,
  )
}
