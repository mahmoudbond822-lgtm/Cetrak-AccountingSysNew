import { useEffect, useRef, useState } from 'react'
import { color, font, radius, shadow, space, z } from '../../lib/tokens'
import { cn } from '../../lib/cn'

const menuStyle = {
  position: 'absolute',
  minWidth: '200px',
  background: color.bg.elevated,
  border: `1px solid ${color.border.default}`,
  borderRadius: radius.md,
  boxShadow: shadow.md,
  zIndex: z.dropdown,
  padding: `${space[1]} 0`,
  listStyle: 'none',
  margin: 0,
}

const itemBaseStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[2],
  width: '100%',
  textAlign: 'left',
  padding: `${space[2]} ${space[3]}`,
  fontSize: font.size.bodySmall,
  color: color.text.primary,
  background: 'none',
  border: 'none',
  cursor: 'pointer',
}

const itemDangerStyle = { color: color.semantic.danger }

/**
 * Dropdown — accessible menu.
 *
 * Opens on click; closes on outside click, Escape, or item selection. Keyboard:
 * focus moves into the menu on open; items are real buttons/links.
 *
 * `items: [{ label, onClick, tone: 'danger', icon, as, to }]`
 */
export default function Dropdown({ trigger, items, align = 'right', className, menuClassName, style }) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)
  const menuRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined

    function handlePointerDown(e) {
      if (!containerRef.current?.contains(e.target)) setOpen(false)
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setOpen(false)
        return
      }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault()
        const focusables = Array.from(
          menuRef.current?.querySelectorAll('button, [href]') || [],
        ).filter((el) => el.offsetParent !== null)
        if (focusables.length === 0) return
        const idx = focusables.indexOf(document.activeElement)
        const next = e.key === 'ArrowDown'
          ? (idx + 1) % focusables.length
          : (idx - 1 + focusables.length) % focusables.length
        focusables[next].focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    menuRef.current?.querySelector('button, [href]')?.focus()

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  function handleItemClick(item) {
    setOpen(false)
    item.onClick?.()
  }

  return (
    <div
      ref={containerRef}
      className={cn(className)}
      style={{ position: 'relative', display: 'inline-flex', ...style }}
    >
      <span
        style={{ display: 'inline-flex' }}
        onClick={() => setOpen((v) => !v)}
        role="presentation"
      >
        {typeof trigger === 'function' ? trigger({ open }) : trigger}
      </span>
      {open && (
        <ul
          ref={menuRef}
          className={cn(menuClassName)}
          role="menu"
          style={{
            ...menuStyle,
            right: align === 'right' ? 0 : 'auto',
            left: align === 'left' ? 0 : 'auto',
            top: 'calc(100% + 4px)',
          }}
        >
          {items.map((item, i) => {
            const isDanger = item.tone === 'danger'
            const content = (
              <>
                {item.icon}
                <span>{item.label}</span>
              </>
            )
            return (
              <li key={i} role="none">
                {item.href ? (
                  <a
                    href={item.href}
                    role="menuitem"
                    style={{ ...itemBaseStyle, ...(isDanger ? itemDangerStyle : null) }}
                    onClick={() => handleItemClick(item)}
                  >
                    {content}
                  </a>
                ) : (
                  <button
                    type="button"
                    role="menuitem"
                    style={{ ...itemBaseStyle, ...(isDanger ? itemDangerStyle : null) }}
                    onClick={() => handleItemClick(item)}
                  >
                    {content}
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
