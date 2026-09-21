import { color, font } from '../../lib/tokens'
import Modal from './Modal'
import Button from './Button'

const descriptionStyle = {
  fontSize: font.size.bodySmall,
  color: color.text.secondary,
  lineHeight: font.leading.normal,
}

/**
 * ConfirmDialog — standardized confirmation for state-changing actions.
 *
 * Replaces every native `window.confirm()` (12 call sites) with a styled, accessible
 * dialog. Use `tone="danger"` for destructive actions so they are visually distinct
 * from normal ones.
 */
export default function ConfirmDialog({
  open,
  onConfirm,
  onCancel,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  tone = 'default',
  loading = false,
}) {
  const isDanger = tone === 'danger'

  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      size="sm"
      closeOnOverlayClick={!loading}
      footer={
        <>
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={isDanger ? 'danger' : 'primary'}
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {description && (
        <div style={descriptionStyle}>
          {description}
        </div>
      )}
    </Modal>
  )
}
