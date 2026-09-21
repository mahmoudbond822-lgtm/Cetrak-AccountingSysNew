import api from './api'

export const accountingService = {
  getAccounts: (params) => api.get('/accounting/accounts/', { params }),
  createAccount: (data) => api.post('/accounting/accounts/', data),
  updateAccount: (id, data) => api.patch(`/accounting/accounts/${id}/`, data),
  deleteAccount: (id) => api.delete(`/accounting/accounts/${id}/`),

  getJournalEntries: (params) => api.get('/accounting/journal-entries/', { params }),
  createJournalEntry: (data) => api.post('/accounting/journal-entries/', data),
  postJournalEntry: (id) => api.post(`/accounting/journal-entries/${id}/post/`),
  getNextJournalReference: () => api.get('/accounting/journal-entries/next-reference/'),

  getLedger: (params) => api.get('/accounting/ledger/', { params }),

  getTrialBalance: (params) => api.get('/accounting/reports/trial-balance/', { params }),
  getIncomeStatement: (params) => api.get('/accounting/reports/income-statement/', { params }),
  getBalanceSheet: (params) => api.get('/accounting/reports/balance-sheet/', { params }),
}
