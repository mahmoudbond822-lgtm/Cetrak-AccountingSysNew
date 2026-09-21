import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ToastProvider } from './components/ui'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import TenantSelectPage from './pages/TenantSelectPage'
import TeamPage from './pages/TeamPage'
import AccountsPage from './pages/accounting/AccountsPage'
import JournalPage from './pages/accounting/JournalPage'
import LedgerPage from './pages/accounting/LedgerPage'
import ReportsPage from './pages/accounting/ReportsPage'
import CustomersPage from './pages/sales/CustomersPage'
import InvoicesPage from './pages/sales/InvoicesPage'
import PaymentsPage from './pages/sales/PaymentsPage'
import SalesSettingsPage from './pages/sales/SalesSettingsPage'
import VendorsPage from './pages/purchases/VendorsPage'
import PurchaseInvoicesPage from './pages/purchases/PurchaseInvoicesPage'
import PurchasePaymentsPage from './pages/purchases/PurchasePaymentsPage'
import PurchasesSettingsPage from './pages/purchases/PurchasesSettingsPage'
import ProductsPage from './pages/inventory/ProductsPage'
import StockPage from './pages/inventory/StockPage'
import AdjustmentsPage from './pages/inventory/AdjustmentsPage'
import InventorySettingsPage from './pages/inventory/InventorySettingsPage'
import ProtectedRoute from './components/layout/ProtectedRoute'
import AppShell from './components/layout/AppShell'

function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/tenant-select"
            element={
              <ProtectedRoute>
                <TenantSelectPage />
              </ProtectedRoute>
            }
          />
          <Route element={<AppShell />}>
            <Route
              path="/team"
              element={
                <ProtectedRoute>
                  <TeamPage />
                </ProtectedRoute>
              }
            />
          <Route
            path="/accounting/accounts"
            element={
              <ProtectedRoute>
                <AccountsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/accounting/journal"
            element={
              <ProtectedRoute>
                <JournalPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/accounting/ledger/:accountId"
            element={
              <ProtectedRoute>
                <LedgerPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/accounting/reports"
            element={
              <ProtectedRoute>
                <ReportsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sales/customers"
            element={
              <ProtectedRoute>
                <CustomersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sales/invoices"
            element={
              <ProtectedRoute>
                <InvoicesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sales/payments"
            element={
              <ProtectedRoute>
                <PaymentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sales/settings"
            element={
              <ProtectedRoute>
                <SalesSettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/purchases/vendors"
            element={
              <ProtectedRoute>
                <VendorsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/purchases/invoices"
            element={
              <ProtectedRoute>
                <PurchaseInvoicesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/purchases/payments"
            element={
              <ProtectedRoute>
                <PurchasePaymentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/purchases/settings"
            element={
              <ProtectedRoute>
                <PurchasesSettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/inventory/products"
            element={
              <ProtectedRoute>
                <ProductsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/inventory/stock"
            element={
              <ProtectedRoute>
                <StockPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/inventory/adjustments"
            element={
              <ProtectedRoute>
                <AdjustmentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/inventory/settings"
            element={
              <ProtectedRoute>
                <InventorySettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
        </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}

export default App
