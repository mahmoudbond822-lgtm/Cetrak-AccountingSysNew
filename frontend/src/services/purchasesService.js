import api from './api'

export const purchasesService = {
  getVendors: (params) => api.get('/purchases/vendors/', { params }),
  createVendor: (data) => api.post('/purchases/vendors/', data),
  updateVendor: (id, data) => api.patch(`/purchases/vendors/${id}/`, data),
  deleteVendor: (id) => api.delete(`/purchases/vendors/${id}/`),

  getInvoices: (params) => api.get('/purchases/invoices/', { params }),
  getInvoice: (id) => api.get(`/purchases/invoices/${id}/`),
  createInvoice: (data) => api.post('/purchases/invoices/', data),
  updateInvoice: (id, data) => api.patch(`/purchases/invoices/${id}/`, data),
  deleteInvoice: (id) => api.delete(`/purchases/invoices/${id}/`),
  postInvoice: (id) => api.post(`/purchases/invoices/${id}/post_invoice/`),

  getPayments: (params) => api.get('/purchases/payments/', { params }),
  getPayment: (id) => api.get(`/purchases/payments/${id}/`),
  createPayment: (data) => api.post('/purchases/payments/', data),
  updatePayment: (id, data) => api.patch(`/purchases/payments/${id}/`, data),
  deletePayment: (id) => api.delete(`/purchases/payments/${id}/`),
  postPayment: (id) => api.post(`/purchases/payments/${id}/post_payment/`),

  getSettings: () => api.get('/purchases/settings/current/'),
  updateSettings: (data) => api.put('/purchases/settings/current/', data),
}