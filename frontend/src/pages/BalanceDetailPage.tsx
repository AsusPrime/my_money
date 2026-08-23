import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAllBalances, useBalanceAmounts } from '../api/balances'
import { useCategories } from '../api/categories'
import { useCurrencies } from '../api/currencies'
import { useBalanceLedger, useRecordOperation, type OperationPayload } from '../api/ledger'
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

function LedgerHistory({ balanceId }: { balanceId: number }) {
  const { data: entries, isLoading } = useBalanceLedger(balanceId)

  if (isLoading) return <p className="text-text-muted">Loading…</p>
  if (entries && entries.length === 0) {
    return <p className="text-text-muted">No operations recorded yet.</p>
  }

  return (
    <ul className="flex flex-col gap-2">
      {entries?.map((entry) => (
        <li
          key={entry.id}
          className="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface p-3"
        >
          <div>
            <div className="text-text">
              {entry.operation_type}
              {entry.counterparty && (
                <span className="text-text-muted"> · {entry.counterparty}</span>
              )}
            </div>
            <div className="text-xs text-text-muted">
              {new Date(entry.executed_at).toLocaleString()}
              {entry.note && ` · ${entry.note}`}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`font-mono font-semibold ${amountColor(entry.amount)}`}>
              {Number(entry.amount) > 0 ? '+' : ''}
              {formatAmount(entry.amount)} {entry.currency_ticker}
            </span>
            <div className="flex gap-2 text-xs font-medium">
              <button
                disabled
                title="Not available yet — backend support coming soon"
                className="cursor-not-allowed text-text-muted opacity-40"
              >
                Edit
              </button>
              <button
                disabled
                title="Not available yet — backend support coming soon"
                className="cursor-not-allowed text-negative opacity-40"
              >
                Delete
              </button>
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}

function RecordOperationForm({ balanceId }: { balanceId: number }) {
  const [operationType, setOperationType] = useState<OperationType>('income')
  const [amount, setAmount] = useState('')
  const [receivedAmount, setReceivedAmount] = useState('')
  const [currencyTicker, setCurrencyTicker] = useState('')
  const [receivedCurrencyTicker, setReceivedCurrencyTicker] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [counterparty, setCounterparty] = useState('')
  const [note, setNote] = useState('')
  const [toBalanceId, setToBalanceId] = useState('')
  const [spendAmount, setSpendAmount] = useState('')
  const [spendCurrency, setSpendCurrency] = useState('')
  const [receiveAmount, setReceiveAmount] = useState('')
  const [receiveCurrency, setReceiveCurrency] = useState('')
  const [executedAtDate, setExecutedAtDate] = useState('')
  const [executedAtTime, setExecutedAtTime] = useState('')
  const [baseCurrencyRate, setBaseCurrencyRate] = useState('')

  const { data: currencies } = useCurrencies()
  const { data: categories } = useCategories()
  const { data: allBalances } = useAllBalances()
  const recordOperation = useRecordOperation()

  const otherBalances = allBalances?.filter((b) => b.id !== balanceId) ?? []

  function resetAmountFields() {
    setAmount('')
    setReceivedAmount('')
    setReceivedCurrencyTicker('')
    setCategoryId('')
    setCounterparty('')
    setNote('')
    setToBalanceId('')
    setSpendAmount('')
    setReceiveAmount('')
    setExecutedAtDate('')
    setExecutedAtTime('')
    setBaseCurrencyRate('')
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()

    let payload: OperationPayload
    // combine the separate date/time inputs (both naive, browser-local) into a
    // real UTC instant, matching what the backend defaults to
    const executedAtIso = executedAtDate
      ? new Date(`${executedAtDate}T${executedAtTime || '00:00'}`).toISOString()
      : undefined

    if (operationType === 'income' || operationType === 'expense' || operationType === 'fee') {
      if (!amount || !currencyTicker) return
      payload = {
        operation_type: operationType,
        balance_id: balanceId,
        amount,
        currency_ticker: currencyTicker,
        category_id: categoryId ? Number(categoryId) : undefined,
        counterparty: counterparty || undefined,
        note: note || undefined,
        executed_at: executedAtIso,
        base_currency_rate: baseCurrencyRate || undefined,
      }
    } else if (operationType === 'transfer') {
      if (!amount || !currencyTicker || !toBalanceId) return
      payload = {
        operation_type: 'transfer',
        from_balance_id: balanceId,
        to_balance_id: Number(toBalanceId),
        amount,
        received_amount: receivedAmount || undefined,
        currency_ticker: currencyTicker,
        received_currency_ticker: receivedCurrencyTicker || undefined,
        note: note || undefined,
        executed_at: executedAtIso,
        base_currency_rate: baseCurrencyRate || undefined,
      }
    } else {
      if (!spendAmount || !spendCurrency || !receiveAmount || !receiveCurrency) return
      payload = {
        operation_type: 'trade',
        balance_id: balanceId,
        spend_amount: spendAmount,
        spend_currency_ticker: spendCurrency,
        receive_amount: receiveAmount,
        receive_currency_ticker: receiveCurrency,
        note: note || undefined,
        executed_at: executedAtIso,
        base_currency_rate: baseCurrencyRate || undefined,
      }
    }

    recordOperation.mutate(payload, { onSuccess: resetAmountFields })
  }

  const currencySelect = (value: string, onChange: (v: string) => void) => (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
    >
      <option value="">Currency</option>
      {currencies?.map((c) => (
        <option key={c.ticker} value={c.ticker}>
          {c.ticker}
        </option>
      ))}
    </select>
  )

  return (
    <form onSubmit={handleSubmit} className="mb-6 flex flex-col gap-2 rounded-lg border border-border bg-surface p-4">
      <select
        value={operationType}
        onChange={(e) => {
          setOperationType(e.target.value as OperationType)
          resetAmountFields()
        }}
        className="rounded-lg border border-border bg-surface-alt px-3 py-2 text-text focus:border-accent focus:outline-none"
      >
        {OPERATION_TYPES.map((type) => (
          <option key={type} value={type}>
            {type}
          </option>
        ))}
      </select>

      {(operationType === 'income' || operationType === 'expense' || operationType === 'fee') && (
        <div className="flex flex-wrap gap-2">
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Amount"
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          {currencySelect(currencyTicker, setCurrencyTicker)}
          <select
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
          >
            <option value="">Category (optional)</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <input
            value={counterparty}
            onChange={(e) => setCounterparty(e.target.value)}
            placeholder="Counterparty (optional)"
            className="flex-1 min-w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
        </div>
      )}

      {operationType === 'transfer' && (
        <div className="flex flex-wrap gap-2">
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Amount sent"
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          {currencySelect(currencyTicker, setCurrencyTicker)}
          <span className="self-center text-text-muted">→</span>
          <input
            value={receivedAmount}
            onChange={(e) => setReceivedAmount(e.target.value)}
            placeholder="Amount received (optional)"
            className="w-40 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          {currencySelect(receivedCurrencyTicker, setReceivedCurrencyTicker)}
          <select
            value={toBalanceId}
            onChange={(e) => setToBalanceId(e.target.value)}
            className="flex-1 min-w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
          >
            <option value="">To balance…</option>
            {otherBalances.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
          <p className="w-full text-xs text-text-muted">
            Leave "received" currency empty for a same-currency transfer. Pick a different
            currency (e.g. moving UAH into a USDT balance via P2P) — then amount received is
            required.
          </p>
        </div>
      )}

      {operationType === 'trade' && (
        <div className="flex flex-wrap gap-2">
          <input
            value={spendAmount}
            onChange={(e) => setSpendAmount(e.target.value)}
            placeholder="Spend amount"
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          {currencySelect(spendCurrency, setSpendCurrency)}
          <span className="self-center text-text-muted">→</span>
          <input
            value={receiveAmount}
            onChange={(e) => setReceiveAmount(e.target.value)}
            placeholder="Receive amount"
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          {currencySelect(receiveCurrency, setReceiveCurrency)}
        </div>
      )}

      <div className="flex gap-2">
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Note (optional)"
          className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
        <input
          type="date"
          value={executedAtDate}
          onChange={(e) => setExecutedAtDate(e.target.value)}
          title="Date (defaults to now if left empty)"
          className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
        />
        <input
          type="time"
          value={executedAtTime}
          onChange={(e) => setExecutedAtTime(e.target.value)}
          title="Time (defaults to 00:00 if left empty; ignored without a date)"
          className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
        />
        <input
          value={baseCurrencyRate}
          onChange={(e) => setBaseCurrencyRate(e.target.value)}
          placeholder="Rate (optional)"
          title="Rate to base currency at execution time — auto-filled for foreign-currency income/expense/fee if left empty; set it to override"
          className="w-28 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={recordOperation.isPending}
          className="rounded-lg bg-accent px-4 py-2 font-semibold text-black transition-colors hover:bg-accent-hover disabled:opacity-50"
        >
          Record
        </button>
      </div>
    </form>
  )
}

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
  const [currencyTicker, setCurrencyTicker] = useState(existing?.currency_ticker ?? '')
  const [categoryId, setCategoryId] = useState(existing?.category_id?.toString() ?? '')
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

  const { data: currencies } = useCurrencies()
  const { data: categories } = useCategories()
  const createRecurringOperation = useCreateRecurringOperation()
  const updateRecurringOperation = useUpdateRecurringOperation()

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!amountValue || (!existing && !currencyTicker)) return

    if (existing) {
      // schedule fields are not part of RecurringOperationUpdatePayload —
      // rescheduling means deleting this operation and creating a new one
      const payload: RecurringOperationUpdatePayload = {
        amount_mode: amountMode,
        amount_value: amountValue,
        category_id: categoryId ? Number(categoryId) : undefined,
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
        category_id: categoryId ? Number(categoryId) : undefined,
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
        },
      })
    }
  }

  const isPending = createRecurringOperation.isPending || updateRecurringOperation.isPending

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-3 flex flex-col gap-2 rounded-lg border border-border bg-surface p-4"
    >
      <div className="flex flex-wrap gap-2">
        {!existing && (
          <select
            value={operationType}
            onChange={(e) => setOperationType(e.target.value as RecurringOperationType)}
            className="rounded-lg border border-border bg-surface-alt px-3 py-2 text-text focus:border-accent focus:outline-none"
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
        {!existing && (
          <select
            value={currencyTicker}
            onChange={(e) => setCurrencyTicker(e.target.value)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
          >
            <option value="">Currency</option>
            {currencies?.map((c) => (
              <option key={c.ticker} value={c.ticker}>
                {c.ticker}
              </option>
            ))}
          </select>
        )}
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
        >
          <option value="">Category (optional)</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
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
            className="rounded-lg border border-border bg-surface-alt px-3 py-2 text-text focus:border-accent focus:outline-none"
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
            className="rounded-lg border border-border bg-surface px-3 py-2 text-text focus:border-accent focus:outline-none"
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

function RecurringOperationsList({ balanceId }: { balanceId: number }) {
  const { data: operations, isLoading } = useRecurringOperationsByBalance(balanceId)
  const deleteRecurringOperation = useDeleteRecurringOperation()
  const updateRecurringOperation = useUpdateRecurringOperation()
  const [editingId, setEditingId] = useState<number | null>(null)

  if (isLoading) return <p className="text-text-muted">Loading…</p>
  if (operations && operations.length === 0) {
    return <p className="text-text-muted">No recurring operations set up yet.</p>
  }

  return (
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
            className="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface p-3"
          >
            <div>
              <div className="text-text">
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
            <div className="flex gap-2 text-xs font-medium">
              <button
                onClick={() => setEditingId(op.id)}
                className="text-text-muted hover:text-text"
              >
                Edit
              </button>
              <button
                onClick={() =>
                  updateRecurringOperation.mutate({
                    id: op.id,
                    payload: { is_active: !op.is_active },
                  })
                }
                className="text-text-muted hover:text-text"
              >
                {op.is_active ? 'Pause' : 'Resume'}
              </button>
              <button
                onClick={() => deleteRecurringOperation.mutate(op.id)}
                className="text-negative hover:opacity-80"
              >
                Delete
              </button>
            </div>
          </li>
        ),
      )}
    </ul>
  )
}

export function BalanceDetailPage() {
  const { balanceId } = useParams<{ balanceId: string }>()
  const id = Number(balanceId)
  const { data: amounts } = useBalanceAmounts(id)
  const amountEntries = Object.entries(amounts ?? {}).filter(([, value]) => Number(value) !== 0)

  return (
    <div className="mx-auto max-w-xl">
      <Link to="/balances" className="mb-4 inline-block text-sm text-text-muted hover:text-text">
        ← Balances
      </Link>
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-xl font-bold text-text">Balance #{id}</h2>
        <div className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-sm text-text">
          {amountEntries.length === 0 ? (
            <span className="text-text-muted">No activity yet</span>
          ) : (
            amountEntries.map(([ticker, value]) => (
              <span key={ticker}>
                {formatAmount(value)} <span className="text-text-muted">{ticker}</span>
              </span>
            ))
          )}
        </div>
      </div>
      <RecordOperationForm balanceId={id} />
      <LedgerHistory balanceId={id} />

      <h3 className="mb-2 mt-6 text-sm font-semibold uppercase tracking-wide text-text-muted">
        Recurring Operations
      </h3>
      <RecurringOperationForm balanceId={id} />
      <RecurringOperationsList balanceId={id} />
    </div>
  )
}
