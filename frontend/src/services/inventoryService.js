import api from './api'

export const inventoryService = {
  getProducts: (params) => api.get('/inventory/products/', { params }),
  getProduct: (id) => api.get(`/inventory/products/${id}/`),
  createProduct: (data) => api.post('/inventory/products/', data),
  updateProduct: (id, data) => api.patch(`/inventory/products/${id}/`, data),
  deleteProduct: (id) => api.delete(`/inventory/products/${id}/`),

  getWarehouses: (params) => api.get('/inventory/warehouses/', { params }),

  getBalances: (params) => api.get('/inventory/stock-balances/', { params }),
  getMovements: (params) => api.get('/inventory/stock-movements/', { params }),

  getAdjustments: (params) => api.get('/inventory/adjustments/', { params }),
  getAdjustment: (id) => api.get(`/inventory/adjustments/${id}/`),
  createAdjustment: (data) => api.post('/inventory/adjustments/', data),
  updateAdjustment: (id, data) => api.patch(`/inventory/adjustments/${id}/`, data),
  deleteAdjustment: (id) => api.delete(`/inventory/adjustments/${id}/`),
  postAdjustment: (id) => api.post(`/inventory/adjustments/${id}/post_adjustment/`),

  getSettings: () => api.get('/inventory/settings/current/'),
  updateSettings: (data) => api.put('/inventory/settings/current/', data),
}