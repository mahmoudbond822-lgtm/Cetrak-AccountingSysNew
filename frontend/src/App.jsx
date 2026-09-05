import { BrowserRouter, Routes, Route } from 'react-router-dom'
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
import SalesSettingsPage from './pages/sales/SalesSettingsPage'
import ProtectedRoute from './components/Layout/ProtectedRoute'

function App() {
  return (
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
          path="/sales/settings"
          element={
            <ProtectedRoute>
              <SalesSettingsPage />
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
      </Routes>
    </BrowserRouter>
  )
}

export default App
