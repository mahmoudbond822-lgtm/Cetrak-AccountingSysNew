/**
 * Cetrak navigation config — the single source of truth for app navigation.
 *
 * Data-driven so new modules (including a future AI group) can be added without
 * touching the shell. Role guards preserve the exact visibility rules that the
 * previous per-module sub-navs enforced.
 *
 * NOTE: no AI links exist here — those routes are not implemented. Adding an
 * `AI` group later is a one-line change.
 */

export const navGroups = [
  {
    id: 'workspace',
    label: 'Workspace',
    items: [
      {
        id: 'sales',
        label: 'Sales',
        to: '/sales/customers',
        children: [
          { label: 'Customers', to: '/sales/customers' },
          { label: 'Invoices', to: '/sales/invoices' },
          { label: 'Payments', to: '/sales/payments' },
          { label: 'Settings', to: '/sales/settings', roles: ['Admin'] },
        ],
      },
      {
        id: 'purchases',
        label: 'Purchases',
        to: '/purchases/vendors',
        children: [
          { label: 'Vendors', to: '/purchases/vendors' },
          { label: 'Purchase Invoices', to: '/purchases/invoices' },
          { label: 'Bills', to: '/purchases/payments' },
          { label: 'Settings', to: '/purchases/settings', roles: ['Admin'] },
        ],
      },
      {
        id: 'inventory',
        label: 'Inventory',
        to: '/inventory/products',
        children: [
          { label: 'Products', to: '/inventory/products' },
          { label: 'Stock', to: '/inventory/stock' },
          { label: 'Adjustments', to: '/inventory/adjustments' },
          { label: 'Settings', to: '/inventory/settings', roles: ['Admin'] },
        ],
      },
    ],
  },
  {
    id: 'accounting',
    label: 'Accounting',
    items: [
      { label: 'Chart of Accounts', to: '/accounting/accounts' },
      { label: 'Journal Entries', to: '/accounting/journal' },
      { label: 'Reports', to: '/accounting/reports', roles: ['Admin', 'Accountant'] },
    ],
  },
  {
    id: 'management',
    label: 'Management',
    items: [{ label: 'Team', to: '/team' }],
  },
]

export const dashboardNavItem = { label: 'Dashboard', to: '/' }

/**
 * Filters nav items by the active tenant role (mirrors the legacy sub-nav guards).
 */
export function filterByRole(items, role) {
  return items.filter((item) => !item.roles || item.roles.includes(role))
}
