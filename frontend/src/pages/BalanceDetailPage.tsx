import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAllBalances, useBalance, useBalanceAmounts, useBalanceTotal } from '../api/balances'
import { useCategories, useCreateCategory } from '../api/categories'
import { useCreateCurrency, useCurrencies, type CurrencyType } from '../api/currencies'
import {
  useBalanceLedger,
  useDeleteOperation,
  useOperationGroup,
  useRecordOperation,
  useReplaceOperation,
  type LedgerEntry,
  type OperationPayload,
} from '../api/ledger'
import {
  useCreateRecurringOperation,
  useDeleteRecurringOperation,
  useRecurringOperationsByBalance,
  useUpdateRecurringOperation,
  type AmountMode,
  type RecurrenceInterval,
  type RecurringOperation,
  type RecurringOperationCreatePayload,
  type RecurringOperationType,
  type RecurringOperationUpdatePayload,
} from '../api/recurringOperations'
import { formatAmount } from '../lib/format'
import { localToUtcSchedule, utcToLocalSchedule } from '../lib/scheduleTimezone'

const OPERATION_TYPES = ['income', 'expense', 'fee', 'transfer', 'trade'] as const
type OperationType = (typeof OPERATION_TYPES)[number]

function amountColor(amount: string) {
  return Number(amount) < 0 ? 'text-negative' : 'text-positive'
}

/* ----------------------------- icons ----------------------------- */

function IconPlus() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

function IconRefresh() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
      <path
        d="M4 4v5h5M20 20v-5h-5M19.5 9A8 8 0 0 0 5.6 6.1M4.5 15a8 8 0 0 0 13.9 2.9"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function IconClose() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function IconPencil() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5">
      <path
        d="M4 20l4-1 11-11-3-3L5 16l-1 4z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function IconTrash() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5">
      <path
        d="M5 7h14M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2m-9 0l1 13a1 1 0 001 1h8a1 1 0 001-1l1-13"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function TypeIcon({ type }: { type: string }) {
  const common = { className: 'h-4 w-4', fill: 'none' as const, viewBox: '0 0 24 24' }
  switch (type) {
    case 'income':
      return (
        <svg {...common}>
          <path
            d="M12 19V5M6 11l6-6 6 6"
            stroke="currentColor"
            strokeWidth="2.3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )
    case 'expense':
      return (
        <svg {...common}>
          <path
            d="M12 5v14M6 13l6 6 6-6"
            stroke="currentColor"
            strokeWidth="2.3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )
    case 'fee':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.8" />
          <path d="M9 9h.01M15 15h.01M9 15l6-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      )
    case 'transfer':
      return (
        <svg {...common}>
          <path
            d="M7 7h11l-3-3m3 3l-3 3M17 17H6l3 3m-3-3l3-3"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )
    case 'trade':
      return (
        <svg {...common}>
          <path
            d="M4 8h13M13 4l4 4-4 4M20 16H7m4 4l-4-4 4-4"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )
    default:
      return null
  }
}

/* ------------------------- overlay primitives ------------------------- */

function useEscapeKey(active: boolean, onClose: () => void) {
  useEffect(() => {
    if (!active) return
    function handler(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [active, onClose])
}

function Drawer({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  useEscapeKey(open, onClose)
  if (!open) return null

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/60" onClick={onClose} />
      <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-border bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h3 className="text-base font-semibold text-text">{title}</h3>
          <button onClick={onClose} className="text-text-muted hover:text-text">
            <IconClose />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </div>
    </>
  )
}

function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  useEscapeKey(open, onClose)
  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h3 className="text-base font-semibold text-text">{title}</h3>
          <button onClick={onClose} className="text-text-muted hover:text-text">
            <IconClose />
          </button>
        </div>
        <div className="overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  )
}

/* ----------------------------- field helper ----------------------------- */

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-text-muted">
        {label}
      </span>
      {children}
    </label>
  )
}

const fieldClass =
  'w-full rounded-lg border border-border bg-surface-alt px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none'

/* ------------------- free-typed currency & category fields ------------------- */
// type-to-select the ticker/category or type a new one — if it doesn't exist
// yet, it's created transparently as part of the same form submit

const inlineFieldClass =
  'rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none'

// mirrors the backend's DEFAULT_DECIMAL_PLACES_BY_CURRENCY_TYPE — pre-fills
// the decimals field when the type changes, but stays user-editable after
const DEFAULT_DECIMAL_PLACES_BY_TYPE: Record<CurrencyType, number> = {
  fiat: 2,
  bond: 2,
  stock: 2,
  crypto: 8,
  other: 2,
}

function useCurrencyField(initial: string = '') {
  const [ticker, setTickerRaw] = useState(initial.toUpperCase())
  const [newType, setNewTypeRaw] = useState<CurrencyType>('fiat')
  const [newDecimalPlaces, setNewDecimalPlaces] = useState(DEFAULT_DECIMAL_PLACES_BY_TYPE.fiat)
  const { data: currencies } = useCurrencies()
  const createCurrency = useCreateCurrency()

  const isLoaded = currencies !== undefined
  const isKnown = !isLoaded || currencies.some((c) => c.ticker === ticker)
  const isNew = ticker.trim() !== '' && isLoaded && !isKnown

  function setNewType(type: CurrencyType) {
    setNewTypeRaw(type)
    setNewDecimalPlaces(DEFAULT_DECIMAL_PLACES_BY_TYPE[type])
  }

  return {
    ticker,
    setTicker: (v: string) => setTickerRaw(v.toUpperCase()),
    isNew,
    newType,
    setNewType,
    newDecimalPlaces,
    setNewDecimalPlaces,
    currencies,
    async resolve(): Promise<string | undefined> {
      if (!ticker) return undefined
      if (!isNew) return ticker
      await createCurrency.mutateAsync({
        ticker,
        currency_type: newType,
        decimal_places: newDecimalPlaces,
      })
      return ticker
    },
  }
}

function useCategoryField(initialCategoryId?: number | null) {
  const [name, setName] = useState('')
  const [resolvedInitial, setResolvedInitial] = useState(false)
  const { data: categories } = useCategories()
  const createCategory = useCreateCategory()

  // category_id -> name can only resolve once the category list has loaded
  useEffect(() => {
    if (resolvedInitial || !categories) return
    if (initialCategoryId != null) {
      const found = categories.find((c) => c.id === initialCategoryId)
      if (found) setName(found.name)
    }
    setResolvedInitial(true)
  }, [categories, initialCategoryId, resolvedInitial])

  return {
    name,
    setName,
    categories,
    async resolve(): Promise<number | undefined> {
      const trimmed = name.trim()
      if (!trimmed) return undefined
      const existing = categories?.find((c) => c.name.toLowerCase() === trimmed.toLowerCase())
      if (existing) return existing.id
      const created = await createCategory.mutateAsync({ name: trimmed })
      return created.id
    },
  }
}

function CurrencyField({
  field,
  className = fieldClass,
  placeholder = 'e.g. USD',
}: {
  field: ReturnType<typeof useCurrencyField>
  className?: string
  placeholder?: string
}) {
  const listId = useId()
  return (
    <div className="min-w-0">
      <input
        list={listId}
        value={field.ticker}
        onChange={(e) => field.setTicker(e.target.value)}
        placeholder={placeholder}
        className={className}
      />
      <datalist id={listId}>
        {field.currencies?.map((c) => <option key={c.ticker} value={c.ticker} />)}
      </datalist>
      {field.isNew && (
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-text-muted">
          <span>New —</span>
          <select
            value={field.newType}
            onChange={(e) => field.setNewType(e.target.value as CurrencyType)}
            className="rounded border border-border bg-surface-alt px-1 py-0.5 text-text focus:border-accent focus:outline-none"
          >
            <option value="fiat">fiat</option>
            <option value="crypto">crypto</option>
            <option value="stock">stock</option>
          </select>
          <input
            type="number"
            min={0}
            max={18}
            value={field.newDecimalPlaces}
            onChange={(e) => field.setNewDecimalPlaces(Number(e.target.value))}
            title="Decimal places — how finely amounts in this currency round"
            className="w-12 rounded border border-border bg-surface-alt px-1 py-0.5 text-text focus:border-accent focus:outline-none"
          />
          <span>decimals, will be added</span>
        </div>
      )}
    </div>
  )
}

function CategoryField({
  field,
  className = fieldClass,
}: {
  field: ReturnType<typeof useCategoryField>
  className?: string
}) {
  const listId = useId()
  return (
    <div className="min-w-0">
      <input
        list={listId}
        value={field.name}
        onChange={(e) => field.setName(e.target.value)}
        placeholder="Category (optional)"
        className={className}
      />
      <datalist id={listId}>
        {field.categories?.map((c) => <option key={c.id} value={c.name} />)}
      </datalist>
    </div>
  )
}

/* ----------------------------- ledger ----------------------------- */

function categoryName(categoryId: number | null, categories: { id: number; name: string }[] | undefined) {
  if (categoryId === null || !categories) return null
  return categories.find((c) => c.id === categoryId)?.name ?? null
}

function LedgerHistory({ balanceId }: { balanceId: number }) {
  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useBalanceLedger(balanceId)
  const { data: categories } = useCategories()
  const [editingLedgerId, setEditingLedgerId] = useState<number | null>(null)
  const { data: editingGroup } = useOperationGroup(editingLedgerId)
  const deleteOperation = useDeleteOperation()
  const sentinelRef = useRef<HTMLLIElement | null>(null)

  const entries = data?.pages.flatMap((page) => page.items)

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel || !hasNextPage) return

    const observer = new IntersectionObserver((observerEntries) => {
      if (observerEntries[0].isIntersecting && !isFetchingNextPage) {
        fetchNextPage()
      }
    })
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [hasNextPage, isFetchingNextPage, fetchNextPage, entries?.length])

  if (isLoading) return <p className="text-text-muted">Loading…</p>
  if (entries && entries.length === 0) {
    return <p className="text-text-muted">No operations recorded yet.</p>
  }

  return (
    <ul className="flex flex-col gap-2">
      {entries?.map((entry) => {
        const isEditing = editingLedgerId === entry.id

        if (isEditing && editingGroup) {
          return (
            <li key={entry.id} className="rounded-lg border border-border bg-surface p-1">
              <EditOperationForm
                balanceId={balanceId}
                ledgerId={entry.id}
                group={editingGroup}
                onDone={() => setEditingLedgerId(null)}
              />
            </li>
          )
        }

        const cat = categoryName(entry.category_id, categories)
        const title = entry.counterparty || cat || entry.operation_type
        const positive = Number(entry.amount) >= 0

        return (
          <li
            key={entry.id}
            className="grid grid-cols-[auto_1fr_auto] items-start gap-x-3 rounded-lg border border-border bg-surface p-3"
          >
            <div
              className={`row-span-2 flex h-8 w-8 items-center justify-center rounded-lg ${
                positive ? 'bg-positive/15 text-positive' : 'bg-negative/15 text-negative'
              }`}
            >
              <TypeIcon type={entry.operation_type} />
            </div>

            <div className="min-w-0">
              <div className="flex items-baseline gap-2 font-medium text-text">
                <span className="truncate">{title}</span>
                {cat && title !== cat && (
                  <span className="shrink-0 rounded bg-surface-alt px-1.5 py-0.5 text-xs text-text-muted">
                    {cat}
                  </span>
                )}
              </div>
              <div className="text-xs text-text-muted">
                {new Date(entry.executed_at).toLocaleString()}
              </div>
              {entry.note && (
                <div className="truncate text-xs text-text-muted" title={entry.note}>
                  {entry.note}
                </div>
              )}
            </div>

            <div className="text-right">
              <div className={`font-mono font-semibold ${amountColor(entry.amount)}`}>
                {positive ? '+' : ''}
                {formatAmount(entry.amount)} {entry.currency_ticker}
              </div>
              <div className="mt-1 flex justify-end gap-1">
                <button
                  onClick={() => setEditingLedgerId(entry.id)}
                  title="Edit"
                  className="flex h-6 w-6 items-center justify-center rounded-md text-text-muted hover:bg-surface-alt hover:text-text"
                >
                  {isEditing ? '…' : <IconPencil />}
                </button>
                <button
                  onClick={() => deleteOperation.mutate(entry.id)}
                  title="Delete"
                  className="flex h-6 w-6 items-center justify-center rounded-md text-text-muted hover:bg-surface-alt hover:text-negative"
                >
                  <IconTrash />
                </button>
              </div>
            </div>
          </li>
        )
      })}
      {hasNextPage && (
        <li ref={sentinelRef} className="py-2 text-center text-xs text-text-muted">
          {isFetchingNextPage ? 'Loading more…' : ''}
        </li>
      )}
    </ul>
  )
}

function toDateInputValue(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function toTimeInputValue(iso: string): string {
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function EditOperationForm({
  balanceId,
  ledgerId,
  group,
  onDone,
}: {
  balanceId: number
  ledgerId: number
  group: LedgerEntry[]
  onDone: () => void
}) {
  const mainLeg = group.find((l) => l.operation_type !== 'fee') ?? group[0]
  const mainType = mainLeg.operation_type as OperationType
  const feeLeg = group.find((l) => l.operation_type === 'fee')
  const primaryLegs = group.filter((l) => l.operation_type === mainType)
  const negativeLeg = primaryLegs.find((l) => Number(l.amount) < 0) ?? mainLeg
  const positiveLeg = primaryLegs.find((l) => Number(l.amount) > 0)

  const { data: allBalances } = useAllBalances()
  const replaceOperation = useReplaceOperation()
  const otherBalances = allBalances?.filter((b) => b.id !== balanceId) ?? []

  const [amount, setAmount] = useState(Math.abs(Number(negativeLeg.amount)).toString())
  const currencyField = useCurrencyField(negativeLeg.currency_ticker)
  const [receivedAmount, setReceivedAmount] = useState(
    positiveLeg ? Math.abs(Number(positiveLeg.amount)).toString() : '',
  )
  const receivedCurrencyField = useCurrencyField(positiveLeg?.currency_ticker ?? '')
  const [toBalanceId, setToBalanceId] = useState(
    mainType === 'transfer' && positiveLeg ? String(positiveLeg.balance_id) : '',
  )
  const categoryField = useCategoryField(mainLeg.category_id)
  const [counterparty, setCounterparty] = useState(
    mainType === 'income' || mainType === 'expense' || mainType === 'fee'
      ? (mainLeg.counterparty ?? '')
      : '',
  )
  const [note, setNote] = useState(mainLeg.note ?? '')
  const [feeAmount, setFeeAmount] = useState(feeLeg ? Math.abs(Number(feeLeg.amount)).toString() : '')
  const feeCurrencyField = useCurrencyField(feeLeg?.currency_ticker ?? '')
  const [executedAtDate, setExecutedAtDate] = useState(toDateInputValue(mainLeg.executed_at))
  const [executedAtTime, setExecutedAtTime] = useState(toTimeInputValue(mainLeg.executed_at))
  const [baseCurrencyRate, setBaseCurrencyRate] = useState(mainLeg.base_currency_rate ?? '')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const executedAtIso = new Date(`${executedAtDate}T${executedAtTime || '00:00'}`).toISOString()

    const currencyTicker = await currencyField.resolve()
    const categoryId = await categoryField.resolve()

    let payload: OperationPayload
    if (mainType === 'income' || mainType === 'expense' || mainType === 'fee') {
      if (!amount || !currencyTicker) return
      payload = {
        operation_type: mainType,
        balance_id: balanceId,
        amount,
        currency_ticker: currencyTicker,
        category_id: categoryId,
        counterparty: counterparty || undefined,
        note: note || undefined,
        executed_at: executedAtIso,
        base_currency_rate: baseCurrencyRate || undefined,
      }
    } else if (mainType === 'transfer') {
      if (!amount || !currencyTicker || !toBalanceId) return
      const receivedCurrencyTicker = await receivedCurrencyField.resolve()
      const feeCurrencyTicker = await feeCurrencyField.resolve()
      payload = {
        operation_type: 'transfer',
        from_balance_id: negativeLeg.balance_id,
        to_balance_id: Number(toBalanceId),
        amount,
        received_amount: receivedAmount || undefined,
        currency_ticker: currencyTicker,
        received_currency_ticker: receivedCurrencyTicker,
        note: note || undefined,
        executed_at: executedAtIso,
        base_currency_rate: baseCurrencyRate || undefined,
        fee_amount: feeAmount || undefined,
        fee_currency_ticker: feeCurrencyTicker,
      }
    } else {
      const receivedCurrencyTicker = await receivedCurrencyField.resolve()
      if (!amount || !currencyTicker || !receivedAmount || !receivedCurrencyTicker) return
      const feeCurrencyTicker = await feeCurrencyField.resolve()
      payload = {
        operation_type: 'trade',
        balance_id: negativeLeg.balance_id,
        spend_amount: amount,
        spend_currency_ticker: currencyTicker,
        receive_amount: receivedAmount,
        receive_currency_ticker: receivedCurrencyTicker,
        note: note || undefined,
        executed_at: executedAtIso,
        base_currency_rate: baseCurrencyRate || undefined,
        fee_amount: feeAmount || undefined,
        fee_currency_ticker: feeCurrencyTicker,
      }
    }

    replaceOperation.mutate({ id: ledgerId, payload }, { onSuccess: onDone })
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-2 rounded-lg border border-accent bg-surface p-3"
    >
      <div className="text-xs font-semibold uppercase text-text-muted">Editing {mainType}</div>

      {(mainType === 'income' || mainType === 'expense' || mainType === 'fee') && (
        <div className="flex flex-wrap gap-2">
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Amount"
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          <CurrencyField field={currencyField} className={inlineFieldClass} />
          <CategoryField field={categoryField} className={inlineFieldClass} />
          <input
            value={counterparty}
            onChange={(e) => setCounterparty(e.target.value)}
            placeholder="Counterparty (optional)"
            className="min-w-32 flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
        </div>
      )}

      {mainType === 'transfer' && (
        <div className="flex flex-wrap gap-2">
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Amount sent"
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          <CurrencyField field={currencyField} className={inlineFieldClass} />
          <span className="self-center text-text-muted">→</span>
          <input
            value={receivedAmount}
            onChange={(e) => setReceivedAmount(e.target.value)}
            placeholder="Amount received"
            className="w-40 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          <CurrencyField field={receivedCurrencyField} className={inlineFieldClass} />
          <select
            value={toBalanceId}
            onChange={(e) => setToBalanceId(e.target.value)}
            className="min-w-32 flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
          >
            <option value="">To balance…</option>
            {otherBalances.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
          <input
            value={feeAmount}
            onChange={(e) => setFeeAmount(e.target.value)}
            placeholder="Fee (optional)"
            className="w-28 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          <CurrencyField field={feeCurrencyField} className={inlineFieldClass} placeholder="Fee currency" />
        </div>
      )}

      {mainType === 'trade' && (
        <div className="flex flex-wrap gap-2">
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Spend amount"
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          <CurrencyField field={currencyField} className={inlineFieldClass} />
          <span className="self-center text-text-muted">→</span>
          <input
            value={receivedAmount}
            onChange={(e) => setReceivedAmount(e.target.value)}
            placeholder="Receive amount"
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          <CurrencyField field={receivedCurrencyField} className={inlineFieldClass} />
          <input
            value={feeAmount}
            onChange={(e) => setFeeAmount(e.target.value)}
            placeholder="Fee (optional)"
            className="w-28 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          <CurrencyField field={feeCurrencyField} className={inlineFieldClass} placeholder="Fee currency" />
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Note (optional)"
          className="min-w-32 flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
        <input
          type="date"
          value={executedAtDate}
          onChange={(e) => setExecutedAtDate(e.target.value)}
          className="w-40 rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
        />
        <input
          type="time"
          value={executedAtTime}
          onChange={(e) => setExecutedAtTime(e.target.value)}
          className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
        />
        <input
          value={baseCurrencyRate}
          onChange={(e) => setBaseCurrencyRate(e.target.value)}
          placeholder="Rate (optional)"
          className="w-28 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={replaceOperation.isPending}
          className="rounded-lg bg-accent px-4 py-2 font-semibold text-black transition-colors hover:bg-accent-hover disabled:opacity-50"
        >
          Save
        </button>
        <button
          type="button"
          onClick={onDone}
          className="rounded-lg border border-border px-4 py-2 text-text-muted hover:text-text"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

function RecordOperationForm({ balanceId, onDone }: { balanceId: number; onDone: () => void }) {
  const [operationType, setOperationType] = useState<OperationType>('income')
  const [amount, setAmount] = useState('')
  const [receivedAmount, setReceivedAmount] = useState('')
  const currencyField = useCurrencyField()
  const receivedCurrencyField = useCurrencyField()
  const categoryField = useCategoryField()
  const [counterparty, setCounterparty] = useState('')
  const [note, setNote] = useState('')
  const [toBalanceId, setToBalanceId] = useState('')
  const [spendAmount, setSpendAmount] = useState('')
  const spendCurrencyField = useCurrencyField()
  const [receiveAmount, setReceiveAmount] = useState('')
  const receiveCurrencyField = useCurrencyField()
  const [feeAmount, setFeeAmount] = useState('')
  const feeCurrencyField = useCurrencyField()
  const [executedAtDate, setExecutedAtDate] = useState('')
  const [executedAtTime, setExecutedAtTime] = useState('')
  const [baseCurrencyRate, setBaseCurrencyRate] = useState('')

  const { data: allBalances } = useAllBalances()
  const recordOperation = useRecordOperation()

  const otherBalances = allBalances?.filter((b) => b.id !== balanceId) ?? []

  function resetFields() {
    setAmount('')
    setReceivedAmount('')
    receivedCurrencyField.setTicker('')
    categoryField.setName('')
    setCounterparty('')
    setNote('')
    setToBalanceId('')
    setSpendAmount('')
    setReceiveAmount('')
    setFeeAmount('')
    feeCurrencyField.setTicker('')
    setExecutedAtDate('')
    setExecutedAtTime('')
    setBaseCurrencyRate('')
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()

    let payload: OperationPayload
    // combine the separate date/time inputs (both naive, browser-local) into a
    // real UTC instant, matching what the backend defaults to
    const executedAtIso = executedAtDate
      ? new Date(`${executedAtDate}T${executedAtTime || '00:00'}`).toISOString()
      : undefined

    if (operationType === 'income' || operationType === 'expense' || operationType === 'fee') {
      const currencyTicker = await currencyField.resolve()
      if (!amount || !currencyTicker) return
      const categoryId = await categoryField.resolve()
      payload = {
        operation_type: operationType,
        balance_id: balanceId,
        amount,
        currency_ticker: currencyTicker,
        category_id: categoryId,
        counterparty: counterparty || undefined,
        note: note || undefined,
        executed_at: executedAtIso,
        base_currency_rate: baseCurrencyRate || undefined,
      }
    } else if (operationType === 'transfer') {
      const currencyTicker = await currencyField.resolve()
      if (!amount || !currencyTicker || !toBalanceId) return
      const receivedCurrencyTicker = await receivedCurrencyField.resolve()
      const feeCurrencyTicker = await feeCurrencyField.resolve()
      payload = {
        operation_type: 'transfer',
        from_balance_id: balanceId,
        to_balance_id: Number(toBalanceId),
        amount,
        received_amount: receivedAmount || undefined,
        currency_ticker: currencyTicker,
        received_currency_ticker: receivedCurrencyTicker,
        fee_amount: feeAmount || undefined,
        fee_currency_ticker: feeCurrencyTicker,
        note: note || undefined,
        executed_at: executedAtIso,
        base_currency_rate: baseCurrencyRate || undefined,
      }
    } else {
      const spendCurrencyTicker = await spendCurrencyField.resolve()
      const receiveCurrencyTicker = await receiveCurrencyField.resolve()
      if (!spendAmount || !spendCurrencyTicker || !receiveAmount || !receiveCurrencyTicker) return
      const feeCurrencyTicker = await feeCurrencyField.resolve()
      payload = {
        operation_type: 'trade',
        balance_id: balanceId,
        spend_amount: spendAmount,
        spend_currency_ticker: spendCurrencyTicker,
        receive_amount: receiveAmount,
        receive_currency_ticker: receiveCurrencyTicker,
        fee_amount: feeAmount || undefined,
        fee_currency_ticker: feeCurrencyTicker,
        note: note || undefined,
        executed_at: executedAtIso,
        base_currency_rate: baseCurrencyRate || undefined,
      }
    }

    recordOperation.mutate(payload, {
      onSuccess: () => {
        resetFields()
        onDone()
      },
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <Field label="Type">
        <select
          value={operationType}
          onChange={(e) => {
            setOperationType(e.target.value as OperationType)
            resetFields()
          }}
          className={fieldClass}
        >
          {OPERATION_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </Field>

      {(operationType === 'income' || operationType === 'expense' || operationType === 'fee') && (
        <>
          <div className="flex gap-2">
            <Field label="Amount">
              <input
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className={fieldClass}
              />
            </Field>
            <Field label="Currency">
              <CurrencyField field={currencyField} className={fieldClass} />
            </Field>
          </div>
          <Field label="Category">
            <CategoryField field={categoryField} className={fieldClass} />
          </Field>
          <Field label="Counterparty">
            <input
              value={counterparty}
              onChange={(e) => setCounterparty(e.target.value)}
              placeholder="Optional"
              className={fieldClass}
            />
          </Field>
        </>
      )}

      {operationType === 'transfer' && (
        <>
          <div className="flex gap-2">
            <Field label="Amount sent">
              <input
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className={fieldClass}
              />
            </Field>
            <Field label="Currency">
              <CurrencyField field={currencyField} className={fieldClass} />
            </Field>
          </div>
          <div className="flex gap-2">
            <Field label="Amount received (optional)">
              <input
                value={receivedAmount}
                onChange={(e) => setReceivedAmount(e.target.value)}
                placeholder="Same as sent"
                className={fieldClass}
              />
            </Field>
            <Field label="Currency">
              <CurrencyField field={receivedCurrencyField} className={fieldClass} />
            </Field>
          </div>
          <Field label="To balance">
            <select
              value={toBalanceId}
              onChange={(e) => setToBalanceId(e.target.value)}
              className={fieldClass}
            >
              <option value="">Select…</option>
              {otherBalances.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </Field>
          <div className="flex gap-2">
            <Field label="Fee (optional)">
              <input
                value={feeAmount}
                onChange={(e) => setFeeAmount(e.target.value)}
                placeholder="0.00"
                className={fieldClass}
              />
            </Field>
            <Field label="Fee currency">
              <CurrencyField
                field={feeCurrencyField}
                className={fieldClass}
                placeholder="Fee currency"
              />
            </Field>
          </div>
          <p className="text-xs text-text-muted">
            Leave "received" currency empty for a same-currency transfer. Pick a different
            currency (e.g. moving UAH into a USDT balance via P2P) — then amount received is
            required.
          </p>
        </>
      )}

      {operationType === 'trade' && (
        <>
          <div className="flex gap-2">
            <Field label="Spend amount">
              <input
                value={spendAmount}
                onChange={(e) => setSpendAmount(e.target.value)}
                placeholder="0.00"
                className={fieldClass}
              />
            </Field>
            <Field label="Currency">
              <CurrencyField field={spendCurrencyField} className={fieldClass} />
            </Field>
          </div>
          <div className="flex gap-2">
            <Field label="Receive amount">
              <input
                value={receiveAmount}
                onChange={(e) => setReceiveAmount(e.target.value)}
                placeholder="0.00"
                className={fieldClass}
              />
            </Field>
            <Field label="Currency">
              <CurrencyField field={receiveCurrencyField} className={fieldClass} />
            </Field>
          </div>
          <div className="flex gap-2">
            <Field label="Fee (optional)">
              <input
                value={feeAmount}
                onChange={(e) => setFeeAmount(e.target.value)}
                placeholder="0.00"
                className={fieldClass}
              />
            </Field>
            <Field label="Fee currency">
              <CurrencyField
                field={feeCurrencyField}
                className={fieldClass}
                placeholder="Fee currency"
              />
            </Field>
          </div>
        </>
      )}

      <Field label="Note">
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Optional"
          className={fieldClass}
        />
      </Field>

      <div className="flex gap-2">
        <Field label="Date">
          <input
            type="date"
            value={executedAtDate}
            onChange={(e) => setExecutedAtDate(e.target.value)}
            title="Defaults to now if left empty"
            className={fieldClass}
          />
        </Field>
        <Field label="Time">
          <input
            type="time"
            value={executedAtTime}
            onChange={(e) => setExecutedAtTime(e.target.value)}
            title="Defaults to 00:00 if left empty; ignored without a date"
            className={fieldClass}
          />
        </Field>
      </div>

      <Field label="Rate (optional)">
        <input
          value={baseCurrencyRate}
          onChange={(e) => setBaseCurrencyRate(e.target.value)}
          placeholder="Auto-filled if left empty"
          className={fieldClass}
        />
      </Field>

      <button
        type="submit"
        disabled={recordOperation.isPending}
        className="mt-2 rounded-lg bg-accent px-4 py-2.5 font-semibold text-black transition-colors hover:bg-accent-hover disabled:opacity-50"
      >
        Record operation
      </button>
    </form>
  )
}

/* --------------------------- recurring operations --------------------------- */

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

function describeDayOfMonth(dayOfMonth: number | null): string {
  if (dayOfMonth === null) return '?'
  if (dayOfMonth > 0) return `day ${dayOfMonth}`
  const n = -dayOfMonth
  return n === 1 ? 'the last day' : `${n} days before the end of the month`
}

function describeSchedule(op: RecurringOperation): string {
  const local = utcToLocalSchedule({
    hour: op.hour,
    minute: op.minute,
    dayOfWeek: op.day_of_week,
    dayOfMonth: op.day_of_month,
    month: op.month,
  })
  const time = `${String(local.hour).padStart(2, '0')}:${String(local.minute).padStart(2, '0')}`
  const day = describeDayOfMonth(local.dayOfMonth)

  switch (op.interval) {
    case 'daily':
      return `Daily at ${time}`
    case 'weekly':
      return `Weekly on ${local.dayOfWeek !== null ? DAY_NAMES[local.dayOfWeek] : '?'} at ${time}`
    case 'monthly':
      return `Monthly on ${day} at ${time}`
    case 'yearly':
      return `Yearly on ${local.month !== null ? MONTH_NAMES[local.month - 1] : '?'} (${day}) at ${time}`
    default:
      return op.interval
  }
}

function RecurringOperationForm({
  balanceId,
  existing,
  onDone,
}: {
  balanceId: number
  existing?: RecurringOperation
  onDone?: () => void
}) {
  const [operationType, setOperationType] = useState<RecurringOperationType>(
    existing?.operation_type ?? 'income',
  )
  const [amountMode, setAmountMode] = useState<AmountMode>(existing?.amount_mode ?? 'fixed')
  const [amountValue, setAmountValue] = useState(existing?.amount_value ?? '')
  const currencyField = useCurrencyField(existing?.currency_ticker ?? '')
  const categoryField = useCategoryField(existing?.category_id ?? null)
  const [counterparty, setCounterparty] = useState(existing?.counterparty ?? '')
  const [note, setNote] = useState(existing?.note ?? '')
  const [interval, setInterval] = useState<RecurrenceInterval>(existing?.interval ?? 'monthly')
  // the backend stores the schedule in UTC; the form always works in the
  // browser's local time, converting at the UTC boundary on load/submit
  const initialLocal = existing
    ? utcToLocalSchedule({
        hour: existing.hour,
        minute: existing.minute,
        dayOfWeek: existing.day_of_week,
        dayOfMonth: existing.day_of_month,
        month: existing.month,
      })
    : { hour: 0, minute: 0, dayOfWeek: 0, dayOfMonth: 1, month: 1 }
  const [dayOfMonth, setDayOfMonth] = useState(String(Math.abs(initialLocal.dayOfMonth ?? 1)))
  const [countFromEnd, setCountFromEnd] = useState((initialLocal.dayOfMonth ?? 1) < 0)
  const [dayOfWeek, setDayOfWeek] = useState(String(initialLocal.dayOfWeek ?? 0))
  const [month, setMonth] = useState(String(initialLocal.month ?? 1))
  const [time, setTime] = useState(
    `${String(initialLocal.hour).padStart(2, '0')}:${String(initialLocal.minute).padStart(2, '0')}`,
  )
  const [isActive, setIsActive] = useState(existing?.is_active ?? true)

  const createRecurringOperation = useCreateRecurringOperation()
  const updateRecurringOperation = useUpdateRecurringOperation()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const currencyTicker = existing ? existing.currency_ticker : await currencyField.resolve()
    if (!amountValue || !currencyTicker) return
    const categoryId = await categoryField.resolve()

    if (existing) {
      // schedule fields are not part of RecurringOperationUpdatePayload —
      // rescheduling means deleting this operation and creating a new one
      const payload: RecurringOperationUpdatePayload = {
        amount_mode: amountMode,
        amount_value: amountValue,
        category_id: categoryId,
        counterparty: counterparty || undefined,
        note: note || undefined,
        is_active: isActive,
      }
      updateRecurringOperation.mutate(
        { id: existing.id, payload },
        { onSuccess: () => onDone?.() },
      )
    } else {
      const [hourStr, minuteStr] = time.split(':')
      const localSchedule = {
        hour: Number(hourStr || 0),
        minute: Number(minuteStr || 0),
        dayOfWeek: interval === 'weekly' ? Number(dayOfWeek) : null,
        dayOfMonth:
          interval === 'monthly' || interval === 'yearly'
            ? countFromEnd
              ? -Number(dayOfMonth)
              : Number(dayOfMonth)
            : null,
        month: interval === 'yearly' ? Number(month) : null,
      }
      const utcSchedule = localToUtcSchedule(localSchedule)
      const payload: RecurringOperationCreatePayload = {
        operation_type: operationType,
        balance_id: balanceId,
        currency_ticker: currencyTicker,
        amount_mode: amountMode,
        amount_value: amountValue,
        category_id: categoryId,
        counterparty: counterparty || undefined,
        note: note || undefined,
        interval,
        day_of_month: utcSchedule.dayOfMonth,
        day_of_week: utcSchedule.dayOfWeek,
        month: utcSchedule.month,
        hour: utcSchedule.hour,
        minute: utcSchedule.minute,
      }
      createRecurringOperation.mutate(payload, {
        onSuccess: () => {
          setAmountValue('')
          setCounterparty('')
          setNote('')
          onDone?.()
        },
      })
    }
  }

  const isPending = createRecurringOperation.isPending || updateRecurringOperation.isPending

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-3 flex flex-col gap-2 rounded-lg border border-border bg-surface-alt p-4"
    >
      <div className="flex flex-wrap gap-2">
        {!existing && (
          <select
            value={operationType}
            onChange={(e) => setOperationType(e.target.value as RecurringOperationType)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
          >
            <option value="income">income</option>
            <option value="expense">expense</option>
            <option value="fee">fee</option>
          </select>
        )}
        <select
          value={amountMode}
          onChange={(e) => setAmountMode(e.target.value as AmountMode)}
          className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
        >
          <option value="fixed">Fixed amount</option>
          <option value="percent_of_balance">% of balance</option>
        </select>
        <input
          value={amountValue}
          onChange={(e) => setAmountValue(e.target.value)}
          placeholder={amountMode === 'fixed' ? 'Amount' : 'Percent (e.g. 2.5)'}
          className="w-36 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
        {!existing && <CurrencyField field={currencyField} className={inlineFieldClass} />}
        <CategoryField field={categoryField} className={inlineFieldClass} />
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          value={counterparty}
          onChange={(e) => setCounterparty(e.target.value)}
          placeholder="Counterparty (optional)"
          className="min-w-32 flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Note (optional)"
          className="min-w-32 flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
      </div>

      {existing ? (
        <p className="text-sm text-text-muted">
          Schedule: {describeSchedule(existing)} — to change it, delete this operation and
          create a new one.
        </p>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={interval}
            onChange={(e) => setInterval(e.target.value as RecurrenceInterval)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="yearly">Yearly</option>
          </select>

          {interval === 'weekly' && (
            <select
              value={dayOfWeek}
              onChange={(e) => setDayOfWeek(e.target.value)}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
            >
              {DAY_NAMES.map((name, i) => (
                <option key={name} value={i}>
                  {name}
                </option>
              ))}
            </select>
          )}

          {interval === 'yearly' && (
            <select
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
            >
              {MONTH_NAMES.map((name, i) => (
                <option key={name} value={i + 1}>
                  {name}
                </option>
              ))}
            </select>
          )}

          {(interval === 'monthly' || interval === 'yearly') && (
            <>
              <input
                type="number"
                min={1}
                max={31}
                value={dayOfMonth}
                onChange={(e) => setDayOfMonth(e.target.value)}
                placeholder="Day"
                className="w-20 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
              />
              <select
                value={countFromEnd ? 'end' : 'start'}
                onChange={(e) => setCountFromEnd(e.target.value === 'end')}
                title="Count the day from the start or from the end of the month"
                className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
              >
                <option value="start">from start of month</option>
                <option value="end">from end of month</option>
              </select>
            </>
          )}

          <input
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            title="Time of day (your local time)"
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
          />
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {existing && (
          <label className="flex items-center gap-1 text-sm text-text-muted">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            Active
          </label>
        )}

        <button
          type="submit"
          disabled={isPending}
          className="ml-auto rounded-lg bg-accent px-4 py-2 font-semibold text-black transition-colors hover:bg-accent-hover disabled:opacity-50"
        >
          {existing ? 'Save' : 'Create'}
        </button>
        {existing && onDone && (
          <button
            type="button"
            onClick={onDone}
            className="rounded-lg border border-border px-4 py-2 text-text-muted hover:text-text"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}

function RecurringOperationsPanel({ balanceId }: { balanceId: number }) {
  const { data: operations, isLoading } = useRecurringOperationsByBalance(balanceId)
  const deleteRecurringOperation = useDeleteRecurringOperation()
  const updateRecurringOperation = useUpdateRecurringOperation()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [creating, setCreating] = useState(false)

  return (
    <div className="flex flex-col gap-2">
      {isLoading && <p className="text-text-muted">Loading…</p>}
      {operations && operations.length === 0 && !creating && (
        <p className="text-text-muted">No recurring operations set up yet.</p>
      )}

      <ul className="flex flex-col gap-2">
        {operations?.map((op) =>
          editingId === op.id ? (
            <RecurringOperationForm
              key={op.id}
              balanceId={balanceId}
              existing={op}
              onDone={() => setEditingId(null)}
            />
          ) : (
            <li
              key={op.id}
              className="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface-alt p-3"
            >
              <div className="min-w-0">
                <div className="truncate text-text">
                  {op.operation_type}
                  {' · '}
                  {op.amount_mode === 'fixed'
                    ? `${formatAmount(op.amount_value)} ${op.currency_ticker}`
                    : `${op.amount_value}% of ${op.currency_ticker} balance`}
                  {!op.is_active && <span className="text-text-muted"> · paused</span>}
                </div>
                <div className="text-xs text-text-muted">
                  {describeSchedule(op)}
                  {op.last_run_at && ` · last ran ${new Date(op.last_run_at).toLocaleString()}`}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <button
                  onClick={() =>
                    updateRecurringOperation.mutate({
                      id: op.id,
                      payload: { is_active: !op.is_active },
                    })
                  }
                  className="rounded-md px-2 py-1 text-xs font-medium text-text-muted hover:bg-surface hover:text-text"
                >
                  {op.is_active ? 'Pause' : 'Resume'}
                </button>
                <button
                  onClick={() => setEditingId(op.id)}
                  title="Edit"
                  className="flex h-6 w-6 items-center justify-center rounded-md text-text-muted hover:bg-surface hover:text-text"
                >
                  <IconPencil />
                </button>
                <button
                  onClick={() => deleteRecurringOperation.mutate(op.id)}
                  title="Delete"
                  className="flex h-6 w-6 items-center justify-center rounded-md text-text-muted hover:bg-surface hover:text-negative"
                >
                  <IconTrash />
                </button>
              </div>
            </li>
          ),
        )}
      </ul>

      {creating ? (
        <RecurringOperationForm balanceId={balanceId} onDone={() => setCreating(false)} />
      ) : (
        <button
          onClick={() => setCreating(true)}
          className="flex items-center justify-center gap-1.5 rounded-lg border border-dashed border-border py-2.5 text-sm font-medium text-text-muted hover:border-accent hover:text-accent"
        >
          <IconPlus />
          New recurring operation
        </button>
      )}
    </div>
  )
}

/* ----------------------------- page ----------------------------- */

export function BalanceDetailPage() {
  const { balanceId } = useParams<{ balanceId: string }>()
  const id = Number(balanceId)
  const { data: balance } = useBalance(id)
  const { data: amounts } = useBalanceAmounts(id)
  const { data: total } = useBalanceTotal(id)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)

  const amountEntries = Object.entries(amounts ?? {}).filter(([, value]) => Number(value) !== 0)

  return (
    <div className="mx-auto max-w-2xl">
      <Link to="/balances" className="mb-4 inline-block text-sm text-text-muted hover:text-text">
        ← Balances
      </Link>

      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <h2 className="text-2xl font-bold text-text">{balance?.name ?? '…'}</h2>

        <div className="text-right">
          {total && (
            <>
              <div className="text-xs uppercase tracking-wide text-text-muted">Total</div>
              <div className="font-mono text-xl font-bold text-text">
                {formatAmount(total.total)}{' '}
                <span className="text-sm text-text-muted">{total.currency_ticker}</span>
              </div>
            </>
          )}
          <div className="mt-1 flex flex-wrap justify-end gap-1.5">
            {amountEntries.length === 0 ? (
              <span className="text-xs text-text-muted">No activity yet</span>
            ) : (
              amountEntries.map(([ticker, value]) => (
                <span
                  key={ticker}
                  className="rounded-full border border-border bg-surface-alt px-2.5 py-0.5 font-mono text-xs text-text-muted"
                >
                  {formatAmount(value)} <span className="text-text">{ticker}</span>
                </span>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="mb-6 flex gap-2">
        <button
          onClick={() => setDrawerOpen(true)}
          className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 font-semibold text-black transition-colors hover:bg-accent-hover"
        >
          <IconPlus />
          Add operation
        </button>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-1.5 rounded-lg border border-border bg-surface-alt px-4 py-2 font-semibold text-text hover:border-text-muted"
        >
          <IconRefresh />
          Recurring
        </button>
      </div>

      <LedgerHistory balanceId={id} />

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Add operation">
        <RecordOperationForm balanceId={id} onDone={() => setDrawerOpen(false)} />
      </Drawer>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Recurring operations">
        <RecurringOperationsPanel balanceId={id} />
      </Modal>
    </div>
  )
}
