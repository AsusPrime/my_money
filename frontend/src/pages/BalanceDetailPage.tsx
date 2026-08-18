import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAllBalances } from '../api/balances'
import { useCurrencies } from '../api/currencies'
import { useBalanceLedger, useRecordOperation, type OperationPayload } from '../api/ledger'

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
          <span className={`font-mono font-semibold ${amountColor(entry.amount)}`}>
            {Number(entry.amount) > 0 ? '+' : ''}
            {entry.amount} {entry.currency_ticker}
          </span>
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
  const [counterparty, setCounterparty] = useState('')
  const [note, setNote] = useState('')
  const [toBalanceId, setToBalanceId] = useState('')
  const [spendAmount, setSpendAmount] = useState('')
  const [spendCurrency, setSpendCurrency] = useState('')
  const [receiveAmount, setReceiveAmount] = useState('')
  const [receiveCurrency, setReceiveCurrency] = useState('')

  const { data: currencies } = useCurrencies()
  const { data: allBalances } = useAllBalances()
  const recordOperation = useRecordOperation()

  const otherBalances = allBalances?.filter((b) => b.id !== balanceId) ?? []

  function resetAmountFields() {
    setAmount('')
    setReceivedAmount('')
    setCounterparty('')
    setNote('')
    setToBalanceId('')
    setSpendAmount('')
    setReceiveAmount('')
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()

    let payload: OperationPayload

    if (operationType === 'income' || operationType === 'expense' || operationType === 'fee') {
      if (!amount || !currencyTicker) return
      payload = {
        operation_type: operationType,
        balance_id: balanceId,
        amount,
        currency_ticker: currencyTicker,
        counterparty: counterparty || undefined,
        note: note || undefined,
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
        note: note || undefined,
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
          <input
            value={receivedAmount}
            onChange={(e) => setReceivedAmount(e.target.value)}
            placeholder="Amount received (optional)"
            className="w-40 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          {currencySelect(currencyTicker, setCurrencyTicker)}
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

export function BalanceDetailPage() {
  const { balanceId } = useParams<{ balanceId: string }>()
  const id = Number(balanceId)

  return (
    <div className="mx-auto max-w-xl">
      <Link to="/balances" className="mb-4 inline-block text-sm text-text-muted hover:text-text">
        ← Balances
      </Link>
      <h2 className="mb-4 text-xl font-bold text-text">Balance #{id}</h2>
      <RecordOperationForm balanceId={id} />
      <LedgerHistory balanceId={id} />
    </div>
  )
}
