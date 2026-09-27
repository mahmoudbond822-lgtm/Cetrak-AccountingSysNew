import { useState, useEffect, useMemo } from 'react'
import { inventoryService } from '../../services/inventoryService'

const wrapperStyle = { display: 'flex', flexDirection: 'column', gap: '0.25rem' }
const labelStyle = { fontSize: '0.8rem', fontWeight: 500, color: 'var(--text)' }

export default function ProductSelect({ value, onChange, includeEmpty = true,
  placeholder = 'Select product...', label, filter = () => true }) {
  const [products, setProducts] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    inventoryService.getProducts({ page_size: 100 })
      .then(({ data }) => setProducts(data.results || []))
      .catch(() => setError('Failed to load products.'))
  }, [])

  const options = useMemo(() => products.filter(filter), [products, filter])

  return (
    <div style={wrapperStyle}>
      {label && <span style={labelStyle}>{label}</span>}
      <select className="cetrak-select" value={value || ''} onChange={(e) => onChange(e.target.value || null)}>
        {includeEmpty && <option value="">{placeholder}</option>}
        {options.map((p) => (
          <option key={p.id} value={p.id}>{p.sku} – {p.name}</option>
        ))}
      </select>
      {error && <span style={{ fontSize: '0.75rem', color: 'var(--danger)' }}>{error}</span>}
    </div>
  )
}