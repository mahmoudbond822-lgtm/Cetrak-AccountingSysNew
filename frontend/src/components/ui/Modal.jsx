import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../../lib/cn'
import { color, font, radius, shadow, space, z } from '../../lib/tokens'

const overlayStyle = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(9, 10, 14, 0.55)',
  zIndex: z.modal,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: space[4],
}

const cardStyle = {
  background: color.bg.elevated,
  borderRadius: radius.lg,
  boxShadow: shadow.lg,
  width: '100%',
  minWidth: 0,
  maxWidth: '520px',
  maxHeight: '85vh',
  overflowY: 'auto',
}

const headerStyle = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: space[3],
  padding: `${space[5]} ${space[5]} ${space[3]}`,
}

const titleStyle = {
  fontSize: font.size.sectionTitle,
  fontWeight: font.weight.semibold,
  color: color.text.primary,
  lineHeight: font.leading.snug,
}

const closeButtonStyle = {
  flexShrink: 0,
  border: 'none',
  background: 'transparent',
  color: color.text.muted,
  cursor: 'pointer',
  padding: '4px',
  borderRadius: radius.sm,
  display: 'inline-flex',
}

const bodyStyle = {
  padding: `0 ${space[5]} ${space[5]}`,
}

const footerStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  gap: space[2],
  padding: `${space[3]} ${space[5]} ${space[5]}`,
}

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

/**
 * Modal — accessible dialog.
 *
 * `role="dialog"`, `aria-modal`, labelled by the title, focus is trapped inside while
 * open and restored to the previously focused element on close, Escape dismisses,
 * overlay click dismisses (disable via `closeOnOverlayClick={false}`), and body scroll
 * is locked while open.
 */
export default function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  closeOnOverlayClick = true,
  closeOnEscape = true,
  className,
  style,
}) {
  const cardRef = useRef(null)
  const [cardId] = useState(() => `cetrak-modal-${Math.random().toString(36).slice(2, 9)}`)

  useEffect(() => {
    if (!open) return undefined

    const previouslyFocused = document.activeElement
    const card = cardRef.current

    function focusFirst() {
      const el = card?.querySelector(FOCUSABLE_SELECTOR)
      if (el) el.focus()
      else card?.focus()
    }

    function handleKeyDown(e) {
      if (closeOnEscape && e.key === 'Escape') {
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key !== 'Tab' || !card) return
      const focusable = Array.from(card.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
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
    focusFirst()

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
      previouslyFocused?.focus?.()
    }
  }, [open, onClose, closeOnEscape])

  if (!open) return null

  const widthBySize = {
    sm: '400px',
    md: '520px',
    lg: '680px',
    xl: '860px',
  }

  return createPortal(
    <div
      className="cetrak-overlay"
      style={overlayStyle}
      onClick={(e) => {
        if (closeOnOverlayClick && e.target === e.currentTarget) onClose()
      }}
      role="presentation"
    >
      <div
        ref={cardRef}
        id={cardId}
        className={cn('cetrak-modal', className)}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? `${cardId}-title` : undefined}
        tabIndex={-1}
        style={{ ...cardStyle, maxWidth: widthBySize[size] || widthBySize.md, ...style }}
      >
        {title && (
          <div style={headerStyle}>
            <div>
              <div id={`${cardId}-title`} style={titleStyle}>{title}</div>
              {description && (
                <div style={{ fontSize: font.size.bodySmall, color: color.text.muted, marginTop: space[1] }}>
                  {description}
                </div>
              )}
            </div>
            <button
              type="button"
              style={closeButtonStyle}
              onClick={onClose}
              aria-label="Close dialog"
              className="cetrak-focus-visible"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
        <div style={bodyStyle}>{children}</div>
        {footer && <div style={footerStyle}>{footer}</div>}
      </div>
    </div>,
    document.body,
  )
}
