import { NavLink, Outlet } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/accounts', label: 'Accounts' },
  { to: '/balances', label: 'Balances' },
  { to: '/categories', label: 'Categories' },
]

function navLinkClass({ isActive }: { isActive: boolean }) {
  return [
    'flex-1 py-2 text-center text-sm font-semibold rounded-lg transition-colors md:flex-none md:text-left md:px-3',
    isActive
      ? 'bg-accent text-black'
      : 'text-text-muted hover:bg-surface-alt hover:text-text',
  ].join(' ')
}

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-bg text-text md:flex-row">
      <nav className="order-2 flex gap-1 border-t border-border bg-surface p-2 md:order-1 md:w-48 md:flex-col md:border-t-0 md:border-r md:p-4">
        <h1 className="hidden px-3 pb-4 text-lg font-bold text-accent md:block">my_money</h1>
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.to} to={item.to} className={navLinkClass}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="order-1 flex-1 overflow-y-auto p-4 md:order-2 md:p-8">
        <Outlet />
      </main>
    </div>
  )
}
