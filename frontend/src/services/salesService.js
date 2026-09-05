import api from './api'

export const salesService = {
  getCustomers: (params) => api.get('/sales/customers/', { params }),
  createCustomer: (data) => api.post('/sales/customers/', data),
  updateCustomer: (id, data) => api.patch(`/sales/customers/${id}/`, data),
  deleteCustomer: (id) => api.delete(`/sales/customers/${id}/`),

  getInvoices: (params) => api.get('/sales/invoices/', { params }),
  getInvoice: (id) => api.get(`/sales/invoices/${id}/`),
  createInvoice: (data) => api.post('/sales/invoices/', data),
  updateInvoice: (id, data) => api.patch(`/sales/invoices/${id}/`, data),
  deleteInvoice: (id) => api.delete(`/sales/invoices/${id}/`),
  postInvoice: (id) => api.post(`/sales/invoices/${id}/post_invoice/`),

  getPayments: (params) => api.get('/sales/payments/', { params }),
  getPayment: (id) => api.get(`/sales/payments/${id}/`),
  createPayment: (data) => api.post('/sales/payments/', data),
  updatePayment: (id, data) => api.patch(`/sales/payments/${id}/`, data),
  deletePayment: (id) => api.delete(`/sales/payments/${id}/`),
  postPayment: (id) => api.post(`/sales/payments/${id}/post_payment/`),

  getSettings: () => api.get('/sales/settings/current/'),
  updateSettings: (data) => api.put('/sales/settings/current/', data),
}