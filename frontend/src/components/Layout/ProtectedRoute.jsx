import { Navigate } from 'react-router-dom'
import { getAuth } from '../../services/api'

export default function ProtectedRoute({ children }) {
  const { accessToken } = getAuth()
  if (!accessToken) {
    return <Navigate to="/login" replace />
  }
  return children
}
