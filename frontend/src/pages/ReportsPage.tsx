import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAccounts } from '../api/accounts'
import { useAllBalances } from '../api/balances'
import { useCategories } from '../api/categories'
import {
  useLedgerReport,
  LEDGER_REPORT_GROUP_BY_OPTIONS,
  LEDGER_REPORT_METRIC_OPTIONS,
  type LedgerReportGroupBy,
  type LedgerReportMetric,
} from '../api/ledgerReport'
import { formatAmount } from '../lib/format'

const OPERATION_TYPES = ['income', 'expense', 'transfer', 'trade', 'fee'] as const

const GROUP_BY_LABELS: Record<LedgerReportGroupBy, string> = {
  category: 'Category',
  counterparty: 'Counterparty',
  operation_type: 'Operation type',
  currency_ticker: 'Currency',
  balance: 'Balance',
  account: 'Account',
  day: 'Day',
  week: 'Week',
  month: 'Month',
  quarter: 'Quarter',
  year: 'Year',
}

const METRIC_LABELS: Record<LedgerReportMetric, string> = {
  sum: 'Sum',
  count: 'Count',
  net_of_fees: 'Sum, net of fees',
}

const selectClass =
  'rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:border-accent focus:outline-none'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-text-muted">{label}</span>
      {children}
    </label>
  )
}

export function ReportsPage() {
  const [groupBy, setGroupBy] = useState<LedgerReportGroupBy>('category')
  const [metric, setMetric] = useState<LedgerReportMetric>('sum')
  const [dateStart, setDateStart] = useState('')
  const [dateEnd, setDateEnd] = useState('')
  const [operationType, setOperationType] = useState('')
  const [currencyTicker, setCurrencyTicker] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [balanceId, setBalanceId] = useState('')
  const [accountId, setAccountId] = useState('')

  const { data: categories } = useCategories()
  const { data: balances } = useAllBalances()
  const { data: accounts } = useAccounts()

  const { data: items, isLoading, isError } = useLedgerReport({
    group_by: groupBy,
    metric,
    date_start: dateStart || undefined,
    date_end: dateEnd || undefined,
    operation_type: operationType || undefined,
    currency_ticker: currencyTicker.trim() || undefined,
    category_id: categoryId ? Number(categoryId) : undefined,
    balance_id: balanceId ? Number(balanceId) : undefined,
    account_id: accountId ? Number(accountId) : undefined,
  })

  const chartData = (items ?? []).map((item) => ({
    name: item.group ?? '—',
    value: Number(item.value),
  }))

  return (
    <div className="mx-auto max-w-4xl">
      <h2 className="mb-4 text-xl font-bold text-text">Reports</h2>

      <div className="mb-6 grid grid-cols-2 gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-3 md:grid-cols-4">
        <Field label="Group by">
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as LedgerReportGroupBy)}
            className={selectClass}
          >
            {LEDGER_REPORT_GROUP_BY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {GROUP_BY_LABELS[option]}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Metric">
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as LedgerReportMetric)}
            className={selectClass}
          >
            {LEDGER_REPORT_METRIC_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {METRIC_LABELS[option]}
              </option>
            ))}
          </select>
        </Field>

        <Field label="From">
          <input
            type="date"
            value={dateStart}
            onChange={(e) => setDateStart(e.target.value)}
            className={selectClass}
          />
        </Field>

        <Field label="To">
          <input
            type="date"
            value={dateEnd}
            onChange={(e) => setDateEnd(e.target.value)}
            className={selectClass}
          />
        </Field>

        <Field label="Operation type">
          <select
            value={operationType}
            onChange={(e) => setOperationType(e.target.value)}
            className={selectClass}
          >
            <option value="">All</option>
            {OPERATION_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Currency">
          <input
            value={currencyTicker}
            onChange={(e) => setCurrencyTicker(e.target.value.toUpperCase())}
            placeholder="All"
            className={selectClass}
          />
        </Field>

        <Field label="Category">
          <select
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            className={selectClass}
          >
            <option value="">All</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Balance">
          <select
            value={balanceId}
            onChange={(e) => setBalanceId(e.target.value)}
            className={selectClass}
          >
            <option value="">All</option>
            {balances?.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Account">
          <select
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            className={selectClass}
          >
            <option value="">All</option>
            {accounts?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </Field>
      </div>

      {isLoading && <p className="text-text-muted">Loading…</p>}
      {isError && <p className="text-negative">Failed to load report.</p>}
      {items && items.length === 0 && (
        <p className="text-text-muted">No data for the given filters.</p>
      )}

      {chartData.length > 0 && (
        <div className="mb-6 rounded-lg border border-border bg-surface p-4">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 48, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2b3139" />
              <XAxis
                dataKey="name"
                stroke="#848e9c"
                tick={{ fill: '#848e9c', fontSize: 12 }}
                angle={-35}
                textAnchor="end"
                interval={0}
              />
              <YAxis stroke="#848e9c" tick={{ fill: '#848e9c', fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: '#1e2329',
                  border: '1px solid #2b3139',
                  borderRadius: 8,
                  color: '#eaecef',
                }}
                labelStyle={{ color: '#eaecef' }}
                formatter={(value) => formatAmount(Number(value))}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={index} fill={entry.value < 0 ? '#f6465d' : '#0ecb81'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {items && items.length > 0 && (
        <ul className="flex flex-col gap-2">
          {items.map((item, index) => (
            <li
              key={index}
              className="flex items-center justify-between rounded-lg border border-border bg-surface p-3"
            >
              <span className="text-text">{item.group ?? '—'}</span>
              <span
                className={`font-mono font-semibold ${
                  Number(item.value) < 0 ? 'text-negative' : 'text-positive'
                }`}
              >
                {formatAmount(item.value)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
