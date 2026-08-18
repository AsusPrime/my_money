import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useAccounts } from '../api/accounts'
import { useArchiveBalance, useBalances, useCreateBalance } from '../api/balances'

function CreateBalanceForm({ accountId }: { accountId: number }) {
  const [name, setName] = useState('')
  const createBalance = useCreateBalance()

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    createBalance.mutate(
      { name: name.trim(), account_id: accountId },
      { onSuccess: () => setName('') },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 flex flex-wrap gap-2">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Balance name (e.g. Cash, Card)"
        className="flex-1 min-w-40 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
      />
      <button
        type="submit"
        disabled={createBalance.isPending}
        className="rounded-lg bg-accent px-4 py-2 font-semibold text-black transition-colors hover:bg-accent-hover disabled:opacity-50"
      >
        Add
      </button>
    </form>
  )
}

export function BalancesPage() {
  const { data: accounts } = useAccounts()
  const activeAccounts = accounts?.filter((account) => !account.is_archived)
  const [accountId, setAccountId] = useState<number | null>(null)
  const selectedAccountId = accountId ?? activeAccounts?.[0]?.id ?? null
  const { data: balances, isLoading } = useBalances(selectedAccountId)
  const activeBalances = balances?.filter((balance) => !balance.is_archived)
  const archiveBalance = useArchiveBalance()

  if (activeAccounts && activeAccounts.length === 0) {
    return (
      <div className="mx-auto max-w-xl text-text-muted">
        Create an account first — balances belong to an account.
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl">
      <h2 className="mb-4 text-xl font-bold text-text">Balances</h2>

      <select
        value={selectedAccountId ?? ''}
        onChange={(e) => setAccountId(Number(e.target.value))}
        className="mb-4 w-full rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
      >
        {activeAccounts?.map((account) => (
          <option key={account.id} value={account.id}>
            {account.name} · {account.base_currency_ticker}
          </option>
        ))}
      </select>

      {selectedAccountId !== null && <CreateBalanceForm accountId={selectedAccountId} />}

      {isLoading && <p className="text-text-muted">Loading…</p>}
      {activeBalances && activeBalances.length === 0 && (
        <p className="text-text-muted">No balances yet for this account.</p>
      )}

      <ul className="flex flex-col gap-2">
        {activeBalances?.map((balance) => (
          <li
            key={balance.id}
            className="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface p-3"
          >
            <Link to={`/balances/${balance.id}`} className="flex-1 text-text hover:text-accent">
              {balance.name}
            </Link>
            <button
              onClick={() => archiveBalance.mutate(balance.id)}
              className="text-sm font-medium text-negative hover:text-negative/80"
            >
              Archive
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
