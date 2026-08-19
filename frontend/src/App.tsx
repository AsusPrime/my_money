import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AccountsPage } from './pages/AccountsPage'
import { BalanceDetailPage } from './pages/BalanceDetailPage'
import { BalancesPage } from './pages/BalancesPage'
import { CategoriesPage } from './pages/CategoriesPage'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/accounts" replace />} />
        <Route path="/accounts" element={<AccountsPage />} />
        <Route path="/balances" element={<BalancesPage />} />
        <Route path="/balances/:balanceId" element={<BalanceDetailPage />} />
        <Route path="/categories" element={<CategoriesPage />} />
      </Route>
    </Routes>
  )
}

export default App
