import { useEffect, useId, useState, type DragEvent, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useAccounts, useAccountTotal } from '../api/accounts'
import {
  useBalanceGroups,
  useCreateBalanceGroup,
  useDeleteBalanceGroup,
  useUpdateBalanceGroup,
  type BalanceGroup,
} from '../api/balanceGroups'
import {
  useArchiveBalance,
  useBalanceAmounts,
  useBalances,
  useBalancesTotalSum,
  useCreateBalance,
  useUpdateBalance,
  type Balance,
} from '../api/balances'
import { formatAmount } from '../lib/format'

function formatAmounts(amounts: Record<string, string> | undefined) {
  if (!amounts) return null
  const entries = Object.entries(amounts).filter(([, value]) => Number(value) !== 0)
  if (entries.length === 0) return null
  return entries.map(([ticker, value]) => `${formatAmount(value)} ${ticker}`).join(' · ')
}

function useBalanceGroupField(accountId: number | null, initialGroupId?: number | null) {
  const [name, setName] = useState('')
  const [resolvedInitial, setResolvedInitial] = useState(false)
  const { data: groups } = useBalanceGroups(accountId)
  const createGroup = useCreateBalanceGroup()

  // group_id -> name can only resolve once the group list has loaded
  useEffect(() => {
    if (resolvedInitial || !groups) return
    if (initialGroupId != null) {
      const found = groups.find((g) => g.id === initialGroupId)
      if (found) setName(found.name)
    }
    setResolvedInitial(true)
  }, [groups, initialGroupId, resolvedInitial])

  return {
    name,
    setName,
    groups,
    async resolve(): Promise<number | null> {
      const trimmed = name.trim()
      if (!trimmed) return null
      const existing = groups?.find((g) => g.name.toLowerCase() === trimmed.toLowerCase())
      if (existing) return existing.id
      if (accountId === null) return null
      const created = await createGroup.mutateAsync({ name: trimmed, account_id: accountId })
      return created.id
    },
  }
}

function BalanceGroupField({
  field,
  className,
}: {
  field: ReturnType<typeof useBalanceGroupField>
  className: string
}) {
  const listId = useId()
  return (
    <div className="min-w-0 flex-1">
      <input
        list={listId}
        value={field.name}
        onChange={(e) => field.setName(e.target.value)}
        placeholder="Group (optional)"
        className={className}
      />
      <datalist id={listId}>
        {field.groups?.map((g) => (
          <option key={g.id} value={g.name} />
        ))}
      </datalist>
    </div>
  )
}

function BalanceRow({ balance, accountId }: { balance: Balance; accountId: number }) {
  const { data: amounts } = useBalanceAmounts(balance.id)
  const archiveBalance = useArchiveBalance()
  const updateBalance = useUpdateBalance()
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(balance.name)
  const groupField = useBalanceGroupField(accountId, balance.group_id)
  const summary = formatAmounts(amounts)

  async function handleSave() {
    if (!name.trim()) {
      setEditing(false)
      return
    }
    const groupId = await groupField.resolve()
    const payload: { name?: string; group_id?: number | null } = {}
    if (name.trim() !== balance.name) payload.name = name.trim()
    if (groupId !== balance.group_id) payload.group_id = groupId
    if (Object.keys(payload).length === 0) {
      setEditing(false)
      return
    }
    updateBalance.mutate({ id: balance.id, payload }, { onSuccess: () => setEditing(false) })
  }

  return (
    <li
      draggable={!editing}
      onDragStart={(e) => {
        e.dataTransfer.setData('text/plain', String(balance.id))
        e.dataTransfer.effectAllowed = 'move'
      }}
      className="flex cursor-grab items-center justify-between gap-2 rounded-lg border border-border bg-surface p-3 active:cursor-grabbing"
    >
      {editing ? (
        <div className="flex flex-1 flex-wrap gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            className="min-w-24 flex-1 rounded border border-border bg-surface-alt px-2 py-1 text-text focus:border-accent focus:outline-none"
          />
          <BalanceGroupField
            field={groupField}
            className="min-w-24 flex-1 rounded border border-border bg-surface-alt px-2 py-1 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
        </div>
      ) : (
        <Link to={`/balances/${balance.id}`} className="flex-1 text-text hover:text-accent">
          <div>{balance.name}</div>
          <div className="text-xs text-text-muted">{summary ?? 'No activity yet'}</div>
        </Link>
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
          onClick={() => archiveBalance.mutate(balance.id)}
          className="text-negative hover:text-negative/80"
        >
          Archive
        </button>
      </div>
    </li>
  )
}

function GroupSectionHeader({
  group,
  total,
  currencyTicker,
  collapsed,
  onToggleCollapse,
}: {
  group: BalanceGroup | null
  total: number | null
  currencyTicker: string | null
  collapsed: boolean
  onToggleCollapse: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(group?.name ?? '')
  const updateGroup = useUpdateBalanceGroup()
  const deleteGroup = useDeleteBalanceGroup()

  function handleSave() {
    if (!group || !name.trim() || name.trim() === group.name) {
      setEditing(false)
      return
    }
    updateGroup.mutate(
      { id: group.id, payload: { name: name.trim() } },
      { onSuccess: () => setEditing(false) },
    )
  }

  return (
    <div className="mb-2 flex items-center justify-between gap-2">
      <div className="flex min-w-0 items-center gap-1.5">
        <button
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand' : 'Collapse'}
          className="text-text-muted hover:text-text"
        >
          {collapsed ? '▸' : '▾'}
        </button>
        {editing && group ? (
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={handleSave}
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            autoFocus
            className="rounded border border-border bg-surface-alt px-2 py-1 text-sm text-text focus:border-accent focus:outline-none"
          />
        ) : (
          <h3
            onClick={() => group && setEditing(true)}
            className={`truncate text-sm font-semibold uppercase tracking-wide text-text-muted ${
              group ? 'cursor-pointer hover:text-text' : ''
            }`}
          >
            {group?.name ?? 'No group'}
          </h3>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {total !== null && (
          <span className="font-mono text-sm text-text-muted">
            {formatAmount(total)} {currencyTicker}
          </span>
        )}
        {group && (
          <button
            onClick={() => deleteGroup.mutate(group.id)}
            title="Delete group — its balances stay, just ungrouped"
            className="text-xs text-text-muted hover:text-negative"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  )
}

function GroupSection({
  group,
  balances,
  accountId,
}: {
  group: BalanceGroup | null
  balances: Balance[]
  accountId: number
}) {
  const [collapsed, setCollapsed] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const { total, currencyTicker } = useBalancesTotalSum(balances.map((b) => b.id))
  const updateBalance = useUpdateBalance()
  const targetGroupId = group?.id ?? null

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragOver(false)
    const balanceId = Number(e.dataTransfer.getData('text/plain'))
    // already in this group — nothing to do
    if (!balanceId || balances.some((b) => b.id === balanceId)) return
    updateBalance.mutate({ id: balanceId, payload: { group_id: targetGroupId } })
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        setIsDragOver(true)
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={`mb-4 rounded-lg p-1 transition-colors ${
        isDragOver ? 'bg-accent/10 ring-2 ring-accent' : ''
      }`}
    >
      <GroupSectionHeader
        group={group}
        total={total}
        currencyTicker={currencyTicker}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
      />
      {!collapsed && (
        <ul className="flex flex-col gap-2">
          {balances.length === 0 ? (
            <li className="rounded-lg border border-dashed border-border p-3 text-center text-xs text-text-muted">
              Drag a balance here
            </li>
          ) : (
            balances.map((balance) => (
              <BalanceRow key={balance.id} balance={balance} accountId={accountId} />
            ))
          )}
        </ul>
      )}
    </div>
  )
}

function CreateGroupForm({ accountId }: { accountId: number }) {
  const [name, setName] = useState('')
  const createGroup = useCreateBalanceGroup()

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    createGroup.mutate(
      { name: name.trim(), account_id: accountId },
      { onSuccess: () => setName('') },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mb-4 flex flex-wrap gap-2">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="New group name (e.g. Investments)"
        className="min-w-40 flex-1 rounded-lg border border-dashed border-border bg-surface-alt px-3 py-2 text-sm text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
      />
      <button
        type="submit"
        disabled={createGroup.isPending}
        className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-text transition-colors hover:border-accent disabled:opacity-50"
      >
        + Group
      </button>
    </form>
  )
}

function CreateBalanceForm({ accountId }: { accountId: number }) {
  const [name, setName] = useState('')
  const groupField = useBalanceGroupField(accountId)
  const createBalance = useCreateBalance()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    const groupId = await groupField.resolve()
    createBalance.mutate(
      { name: name.trim(), account_id: accountId, group_id: groupId },
      {
        onSuccess: () => {
          setName('')
          groupField.setName('')
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 flex flex-wrap gap-2">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Balance name (e.g. Cash, Card)"
        className="min-w-40 flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
      />
      <BalanceGroupField
        field={groupField}
        className="min-w-32 flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
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
  const { data: accountTotal } = useAccountTotal(selectedAccountId)
  const { data: groups } = useBalanceGroups(selectedAccountId)

  if (activeAccounts && activeAccounts.length === 0) {
    return (
      <div className="mx-auto max-w-xl text-text-muted">
        Create an account first — balances belong to an account.
      </div>
    )
  }

  const balancesByGroupId = new Map<number | null, Balance[]>()
  for (const balance of activeBalances ?? []) {
    const bucket = balancesByGroupId.get(balance.group_id)
    if (bucket) bucket.push(balance)
    else balancesByGroupId.set(balance.group_id, [balance])
  }

  // every group gets a section even when empty, so a freshly created group
  // has somewhere to drag balances into
  const sections: { group: BalanceGroup | null; balances: Balance[] }[] = []
  for (const group of groups ?? []) {
    sections.push({ group, balances: balancesByGroupId.get(group.id) ?? [] })
  }
  sections.push({ group: null, balances: balancesByGroupId.get(null) ?? [] })

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <h2 className="text-xl font-bold text-text">Balances</h2>
        {accountTotal && (
          <div className="text-right">
            <div className="text-xs uppercase tracking-wide text-text-muted">Total</div>
            <div className="font-mono text-xl font-bold text-text">
              {formatAmount(accountTotal.total)}{' '}
              <span className="text-sm text-text-muted">{accountTotal.currency_ticker}</span>
            </div>
          </div>
        )}
      </div>

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

      {selectedAccountId !== null && (
        <>
          <CreateGroupForm accountId={selectedAccountId} />
          <CreateBalanceForm accountId={selectedAccountId} />
        </>
      )}

      {isLoading && <p className="text-text-muted">Loading…</p>}
      {activeBalances && activeBalances.length === 0 && (
        <p className="text-text-muted">No balances yet for this account.</p>
      )}

      {selectedAccountId !== null &&
        sections.map((section) => (
          <GroupSection
            key={section.group?.id ?? 'ungrouped'}
            group={section.group}
            balances={section.balances}
            accountId={selectedAccountId}
          />
        ))}
    </div>
  )
}
