import { useState, type FormEvent } from 'react'
import {
  useAccounts,
  useArchiveAccount,
  useCreateAccount,
  useUpdateAccount,
  type Account,
} from '../api/accounts'

function CreateAccountForm() {
  const [name, setName] = useState('')
  const [ticker, setTicker] = useState('USD')
  const createAccount = useCreateAccount()

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    createAccount.mutate(
      { name: name.trim(), base_currency_ticker: ticker.trim() || 'USD' },
      { onSuccess: () => setName('') },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 flex flex-wrap gap-2">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Account name"
        className="flex-1 min-w-40 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
      />
      <input
        value={ticker}
        onChange={(e) => setTicker(e.target.value.toUpperCase())}
        placeholder="USD"
        className="w-24 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
      />
      <button
        type="submit"
        disabled={createAccount.isPending}
        className="rounded-lg bg-accent px-4 py-2 font-semibold text-black transition-colors hover:bg-accent-hover disabled:opacity-50"
      >
        Add
      </button>
    </form>
  )
}

function AccountRow({ account }: { account: Account }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(account.name)
  const updateAccount = useUpdateAccount()
  const archiveAccount = useArchiveAccount()

  function handleSave() {
    if (!name.trim() || name === account.name) {
      setEditing(false)
      return
    }
    updateAccount.mutate(
      { id: account.id, payload: { name: name.trim() } },
      { onSuccess: () => setEditing(false) },
    )
  }

  return (
    <li className="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface p-3">
      {editing ? (
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
          className="flex-1 rounded border border-border bg-surface-alt px-2 py-1 text-text focus:border-accent focus:outline-none"
        />
      ) : (
        <span className="flex-1 text-text">
          {account.name} <span className="text-text-muted">· {account.base_currency_ticker}</span>
        </span>
      )}
      <div className="flex gap-3 text-sm font-medium">
        {editing ? (
          <button onClick={handleSave} className="text-accent hover:text-accent-hover">
            Save
          </button>
        ) : (
          <button onClick={() => setEditing(true)} className="text-text-muted hover:text-text">
            Edit
          </button>
        )}
        <button
          onClick={() => archiveAccount.mutate(account.id)}
          className="text-negative hover:text-negative/80"
        >
          Archive
        </button>
      </div>
    </li>
  )
}

export function AccountsPage() {
  const { data: accounts, isLoading, isError } = useAccounts()
  const activeAccounts = accounts?.filter((account) => !account.is_archived)

  return (
    <div className="mx-auto max-w-xl">
      <h2 className="mb-4 text-xl font-bold text-text">Accounts</h2>
      <CreateAccountForm />
      {isLoading && <p className="text-text-muted">Loading…</p>}
      {isError && <p className="text-negative">Failed to load accounts.</p>}
      {activeAccounts && activeAccounts.length === 0 && (
        <p className="text-text-muted">No accounts yet.</p>
      )}
      <ul className="flex flex-col gap-2">
        {activeAccounts?.map((account) => (
          <AccountRow key={account.id} account={account} />
        ))}
      </ul>
    </div>
  )
}
