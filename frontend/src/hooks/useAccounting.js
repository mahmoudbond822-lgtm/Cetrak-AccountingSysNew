import { useState, useCallback } from 'react'
import { accountingService } from '../services/accountingService'

export function useAccounting() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchAccounts = useCallback(async (params) => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await accountingService.getAccounts(params)
      setAccounts(data)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  return { accounts, loading, error, fetchAccounts }
}
