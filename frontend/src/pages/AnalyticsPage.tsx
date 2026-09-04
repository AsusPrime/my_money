import { useEffect, useRef, useState } from 'react'
import ReactGridLayout, { useContainerWidth, type Layout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  useAnalyticsWidgets,
  useCreateAnalyticsWidget,
  useDeleteAnalyticsWidget,
  useUpdateAnalyticsWidget,
  useUpdateAnalyticsWidgetsLayout,
  CHART_TYPE_OPTIONS,
  DATE_RANGE_PRESET_OPTIONS,
  type AnalyticsWidget,
  type AnalyticsWidgetFilters,
  type AnalyticsWidgetPayload,
  type ChartType,
  type DateRangePreset,
} from '../api/analyticsWidgets'
import { resolveDateRange, DATE_RANGE_PRESET_LABELS } from '../lib/dateRange'
import { useAccounts } from '../api/accounts'
import { useAllBalances } from '../api/balances'
import { useCategories } from '../api/categories'
import {
  useLedgerReport,
  useNetWorthReport,
  LEDGER_REPORT_GROUP_BY_OPTIONS,
  LEDGER_REPORT_METRIC_OPTIONS,
  NET_WORTH_BUCKET_OPTIONS,
  type LedgerReportGroupBy,
  type LedgerReportMetric,
  type NetWorthBucket,
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
  net_worth: 'Net worth (total money over time)',
}

const CHART_TYPE_LABELS: Record<ChartType, string> = {
  bar: 'Bar',
  pie: 'Pie',
  line: 'Line',
}

const TIME_BUCKETS = new Set(['day', 'week', 'month', 'quarter', 'year'])
const QUARTER_LABELS = ['Q1', 'Q2', 'Q3', 'Q4']
const MONTH_LABELS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

const PIE_COLORS = ['#f0b90b', '#0ecb81', '#f6465d', '#848e9c', '#5b8def', '#a970ff', '#3ddc97']

const selectClass =
  'rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:border-accent focus:outline-none'

// keeps the x-axis legible: time buckets get a short "Jan '24" / "Q1 '24"
// label instead of a raw ISO date, and any long label (e.g. Ukrainian
// category names) gets truncated — the tooltip still shows the full value
function formatAxisLabel(name: string, groupBy: string): string {
  if (TIME_BUCKETS.has(groupBy)) {
    const date = new Date(name)
    if (!Number.isNaN(date.getTime())) {
      const year = date.getUTCFullYear().toString().slice(-2)
      if (groupBy === 'year') return date.getUTCFullYear().toString()
      if (groupBy === 'quarter') return `${QUARTER_LABELS[Math.floor(date.getUTCMonth() / 3)]} '${year}`
      if (groupBy === 'month') return `${MONTH_LABELS[date.getUTCMonth()]} '${year}`
      return `${date.getUTCDate()} ${MONTH_LABELS[date.getUTCMonth()]}`
    }
  }
  return name.length > 14 ? `${name.slice(0, 13)}…` : name
}

// shows every label when there's room, otherwise skips enough to keep them
// from overlapping (recharts' interval prop: N means "skip N ticks between
// each rendered one")
function xAxisInterval(pointCount: number): number {
  return Math.max(0, Math.ceil(pointCount / 10) - 1)
}

function Field({
  label,
  children,
  fullWidth,
}: {
  label: string
  children: React.ReactNode
  fullWidth?: boolean
}) {
  return (
    <label className={`flex flex-col gap-1 ${fullWidth ? 'col-span-full' : ''}`}>
      <span className="text-xs uppercase tracking-wide text-text-muted">{label}</span>
      {children}
    </label>
  )
}

// dropdown checkbox multi-select — empty selection means "All" (no filter
// sent), same semantics the old single <select> had for its blank "All"
// option. Closes on outside click, like any normal dropdown.
function MultiSelect<T extends string | number>({
  options,
  selected,
  onChange,
  renderLabel,
}: {
  options: readonly T[]
  selected: T[]
  onChange: (next: T[]) => void
  renderLabel: (option: T) => string
}) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  function toggle(option: T) {
    onChange(
      selected.includes(option) ? selected.filter((o) => o !== option) : [...selected, option],
    )
  }

  const summary =
    selected.length === 0
      ? 'All'
      : selected.length <= 2
        ? selected.map(renderLabel).join(', ')
        : `${selected.length} selected`

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`${selectClass} flex w-full items-center justify-between gap-2 text-left`}
      >
        <span className="truncate">{summary}</span>
        <span className="text-text-muted">{open ? '▴' : '▾'}</span>
      </button>
      {open && (
        <div className="absolute z-10 mt-1 max-h-56 w-full min-w-48 overflow-y-auto rounded-lg border border-border bg-surface p-1 shadow-lg">
          {options.length === 0 && (
            <div className="px-2 py-1.5 text-xs text-text-muted">None available</div>
          )}
          {options.map((option) => (
            <label
              key={option}
              className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm text-text hover:bg-surface-alt"
            >
              <input
                type="checkbox"
                checked={selected.includes(option)}
                onChange={() => toggle(option)}
                className="accent-accent"
              />
              <span className="truncate">{renderLabel(option)}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

const EMPTY_FILTERS: AnalyticsWidgetFilters = {}

function WidgetForm({
  initial,
  onCancel,
  onSaved,
}: {
  initial?: AnalyticsWidget
  onCancel: () => void
  onSaved: () => void
}) {
  const [title, setTitle] = useState(initial?.title ?? '')
  const [chartType, setChartType] = useState<ChartType>(initial?.chart_type ?? 'bar')
  const [groupBy, setGroupBy] = useState<LedgerReportGroupBy>(initial?.group_by ?? 'category')
  const [metric, setMetric] = useState<LedgerReportMetric>(initial?.metric ?? 'sum')
  const filters = initial?.filters ?? EMPTY_FILTERS
  const [dateRangePreset, setDateRangePreset] = useState<DateRangePreset>(
    filters.date_range_preset ?? (filters.date_start || filters.date_end ? 'custom' : 'all'),
  )
  const [dateStart, setDateStart] = useState(filters.date_start?.slice(0, 10) ?? '')
  const [dateEnd, setDateEnd] = useState(filters.date_end?.slice(0, 10) ?? '')
  const [operationTypes, setOperationTypes] = useState<string[]>(filters.operation_types ?? [])
  const [currencyTicker, setCurrencyTicker] = useState(filters.currency_ticker ?? '')
  const [categoryIds, setCategoryIds] = useState<number[]>(filters.category_ids ?? [])
  const [balanceIds, setBalanceIds] = useState<number[]>(filters.balance_ids ?? [])
  const [accountId, setAccountId] = useState(filters.account_id?.toString() ?? '')

  const isNetWorth = metric === 'net_worth'

  // net_worth only makes sense grouped by a time bucket — switching into it
  // from a non-time group_by (e.g. "Category") needs a sane default instead
  // of silently sending an invalid combo
  useEffect(() => {
    if (isNetWorth && !NET_WORTH_BUCKET_OPTIONS.includes(groupBy as NetWorthBucket)) {
      setGroupBy('month')
    }
  }, [isNetWorth, groupBy])

  const { data: categories } = useCategories()
  const { data: balances } = useAllBalances()
  const { data: accounts } = useAccounts()

  const createWidget = useCreateAnalyticsWidget()
  const updateWidget = useUpdateAnalyticsWidget()
  const saving = createWidget.isPending || updateWidget.isPending
  const canSave = title.trim() && (!isNetWorth || currencyTicker.trim())

  function handleSave() {
    if (!canSave) return

    const payload: AnalyticsWidgetPayload = {
      title: title.trim(),
      chart_type: chartType,
      group_by: groupBy,
      metric,
      filters: {
        date_range_preset: dateRangePreset,
        date_start: dateRangePreset === 'custom' ? dateStart || undefined : undefined,
        date_end: dateRangePreset === 'custom' ? dateEnd || undefined : undefined,
        operation_types: operationTypes.length ? operationTypes : undefined,
        currency_ticker: currencyTicker.trim() || undefined,
        category_ids: categoryIds.length ? categoryIds : undefined,
        balance_ids: balanceIds.length ? balanceIds : undefined,
        account_id: accountId ? Number(accountId) : undefined,
      },
    }

    if (initial) {
      updateWidget.mutate({ id: initial.id, payload }, { onSuccess: onSaved })
    } else {
      createWidget.mutate(payload, { onSuccess: onSaved })
    }
  }

  return (
    <div className="mb-6 rounded-lg border border-border bg-surface p-4">
      <div className="mb-3 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
        <Field label="Title">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Expenses by category"
            className={selectClass}
          />
        </Field>

        <Field label="Chart type">
          <select
            value={chartType}
            onChange={(e) => setChartType(e.target.value as ChartType)}
            className={selectClass}
          >
            {CHART_TYPE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {CHART_TYPE_LABELS[option]}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Group by">
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as LedgerReportGroupBy)}
            className={selectClass}
          >
            {(isNetWorth ? NET_WORTH_BUCKET_OPTIONS : LEDGER_REPORT_GROUP_BY_OPTIONS).map(
              (option) => (
                <option key={option} value={option}>
                  {GROUP_BY_LABELS[option]}
                </option>
              ),
            )}
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

        <Field label="Date range">
          <select
            value={dateRangePreset}
            onChange={(e) => setDateRangePreset(e.target.value as DateRangePreset)}
            className={selectClass}
          >
            {DATE_RANGE_PRESET_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {DATE_RANGE_PRESET_LABELS[option]}
              </option>
            ))}
          </select>
        </Field>

        {dateRangePreset === 'custom' && (
          <>
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
          </>
        )}

        <Field label={isNetWorth ? 'Report currency (required)' : 'Currency'}>
          <input
            value={currencyTicker}
            onChange={(e) => setCurrencyTicker(e.target.value.toUpperCase())}
            placeholder={isNetWorth ? 'e.g. UAH' : 'All'}
            className={selectClass}
          />
        </Field>

        {!isNetWorth && (
          <Field label="Operation type (any of, or none = all)" fullWidth>
            <MultiSelect
              options={OPERATION_TYPES}
              selected={operationTypes}
              onChange={setOperationTypes}
              renderLabel={(type) => type}
            />
          </Field>
        )}

        {!isNetWorth && (
          <Field label="Category (any of, or none = all)" fullWidth>
            <MultiSelect
              options={categories?.map((c) => c.id) ?? []}
              selected={categoryIds}
              onChange={setCategoryIds}
              renderLabel={(id) => categories?.find((c) => c.id === id)?.name ?? String(id)}
            />
          </Field>
        )}

        <Field label="Balance (any of, or none = all)" fullWidth>
          <MultiSelect
            options={balances?.map((b) => b.id) ?? []}
            selected={balanceIds}
            onChange={setBalanceIds}
            renderLabel={(id) => balances?.find((b) => b.id === id)?.name ?? String(id)}
          />
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

      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving || !canSave}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-black hover:bg-accent-hover disabled:opacity-50"
        >
          {initial ? 'Save changes' : 'Add widget'}
        </button>
        <button
          onClick={onCancel}
          className="rounded-lg border border-border px-4 py-2 text-sm text-text-muted hover:text-text"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

function useWidgetData(widget: AnalyticsWidget) {
  const isNetWorth = widget.metric === 'net_worth'
  // resolved fresh on every render from "now" — a "this_month" preset must
  // mean the current month whenever the page loads, not the month the
  // widget was created in (see resolveDateRange)
  const { date_start, date_end } = resolveDateRange(
    widget.filters.date_range_preset,
    widget.filters.date_start,
    widget.filters.date_end,
  )

  // both hooks are always called (rules of hooks), but only the one that
  // matches the widget's metric is actually enabled — `enabled: false` skips
  // the fetch entirely rather than firing a request whose result is thrown
  // away (previously every widget fired both /ledger/report AND
  // /ledger/net-worth, the latter often 400-ing since group_by/currency
  // rarely satisfy net-worth's stricter requirements)
  const ledgerReport = useLedgerReport(
    {
      group_by: widget.group_by,
      metric: widget.metric as Exclude<LedgerReportMetric, 'net_worth'>,
      date_start,
      date_end,
      operation_types: widget.filters.operation_types ?? undefined,
      currency_ticker: widget.filters.currency_ticker ?? undefined,
      category_ids: widget.filters.category_ids ?? undefined,
      balance_ids: widget.filters.balance_ids ?? undefined,
      account_id: widget.filters.account_id ?? undefined,
    },
    !isNetWorth,
  )
  const netWorthReport = useNetWorthReport(
    {
      currency_ticker: widget.filters.currency_ticker ?? '',
      group_by: widget.group_by as NetWorthBucket,
      date_start,
      date_end,
      balance_ids: widget.filters.balance_ids ?? undefined,
      account_id: widget.filters.account_id ?? undefined,
    },
    isNetWorth,
  )

  return widget.metric === 'net_worth' ? netWorthReport : ledgerReport
}

function WidgetChart({ widget }: { widget: AnalyticsWidget }) {
  const { data: items, isLoading, isError } = useWidgetData(widget)

  if (isLoading) return <p className="text-text-muted">Loading…</p>
  if (isError) return <p className="text-negative">Failed to load data.</p>
  if (!items || items.length === 0) {
    return <p className="text-text-muted">No data for the given filters.</p>
  }

  const chartData = items.map((item) => ({
    name: item.group ?? '—',
    label: formatAxisLabel(item.group ?? '—', widget.group_by),
    value: Number(item.value),
  }))
  const interval = xAxisInterval(chartData.length)

  const tooltipStyle = {
    contentStyle: {
      background: '#1e2329',
      border: '1px solid #2b3139',
      borderRadius: 8,
      color: '#eaecef',
    },
    labelStyle: { color: '#eaecef' },
  }

  if (widget.chart_type === 'pie') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={chartData} dataKey="value" nameKey="label" outerRadius={90}>
            {chartData.map((_entry, index) => (
              <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip {...tooltipStyle} formatter={(value) => formatAmount(Number(value))} />
          <Legend
            wrapperStyle={{
              color: '#848e9c',
              fontSize: 12,
              maxHeight: 90,
              overflowY: 'auto',
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  if (widget.chart_type === 'line') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 32, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2b3139" />
          <XAxis
            dataKey="label"
            stroke="#848e9c"
            tick={{ fill: '#848e9c', fontSize: 11 }}
            interval={interval}
          />
          <YAxis stroke="#848e9c" tick={{ fill: '#848e9c', fontSize: 12 }} />
          <Tooltip {...tooltipStyle} formatter={(value) => formatAmount(Number(value))} />
          <Line type="monotone" dataKey="value" stroke="#f0b90b" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 32, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2b3139" />
        <XAxis
          dataKey="label"
          stroke="#848e9c"
          tick={{ fill: '#848e9c', fontSize: 11 }}
          interval={interval}
        />
        <YAxis stroke="#848e9c" tick={{ fill: '#848e9c', fontSize: 12 }} />
        <Tooltip {...tooltipStyle} formatter={(value) => formatAmount(Number(value))} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={index} fill={entry.value < 0 ? '#f6465d' : '#0ecb81'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function WidgetCard({ widget, onEdit }: { widget: AnalyticsWidget; onEdit: () => void }) {
  const deleteWidget = useDeleteAnalyticsWidget()

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-surface p-4">
      <div className="mb-2 flex shrink-0 items-center justify-between gap-2">
        <h3 className="truncate font-semibold text-text">{widget.title}</h3>
        <div className="no-drag flex shrink-0 gap-3 text-sm">
          <button onClick={onEdit} className="text-text-muted hover:text-text">
            Edit
          </button>
          <button
            onClick={() => deleteWidget.mutate(widget.id)}
            className="text-negative hover:text-negative/80"
          >
            Delete
          </button>
        </div>
      </div>
      <div className="min-h-0 flex-1">
        <WidgetChart widget={widget} />
      </div>
    </div>
  )
}

const GRID_COLS = 12
const ROW_HEIGHT = 60
const GRID_MARGIN: readonly [number, number] = [16, 16]

function WidgetGrid({
  widgets,
  onEdit,
}: {
  widgets: AnalyticsWidget[]
  onEdit: (id: number) => void
}) {
  const { width, containerRef, mounted } = useContainerWidth()
  const updateLayout = useUpdateAnalyticsWidgetsLayout()

  const [layout, setLayout] = useState<Layout>(() =>
    widgets.map((w) => ({ i: String(w.id), x: w.grid_x, y: w.grid_y, w: w.grid_w, h: w.grid_h })),
  )

  useEffect(() => {
    setLayout(
      widgets.map((w) => ({ i: String(w.id), x: w.grid_x, y: w.grid_y, w: w.grid_w, h: w.grid_h })),
    )
    // widgets is refetched after every layout persist too — resyncing keeps
    // the grid in sync with the server without fighting an in-flight drag
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [widgets])

  function persist(finalLayout: Layout) {
    updateLayout.mutate(
      finalLayout.map((item) => ({
        id: Number(item.i),
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
      })),
    )
  }

  const widgetsById = new Map(widgets.map((w) => [String(w.id), w]))

  return (
    <div ref={containerRef}>
      {mounted && (
        <ReactGridLayout
          layout={layout}
          width={width}
          gridConfig={{ cols: GRID_COLS, rowHeight: ROW_HEIGHT, margin: GRID_MARGIN }}
          dragConfig={{ cancel: '.no-drag' }}
          onLayoutChange={setLayout}
          onDragStop={persist}
          onResizeStop={persist}
        >
          {layout.map((item) => {
            const widget = widgetsById.get(item.i)
            if (!widget) return null
            return (
              <div key={item.i}>
                <WidgetCard widget={widget} onEdit={() => onEdit(widget.id)} />
              </div>
            )
          })}
        </ReactGridLayout>
      )}
    </div>
  )
}

export function AnalyticsPage() {
  const { data: widgets, isLoading } = useAnalyticsWidgets()
  const [adding, setAdding] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)

  const editingWidget = widgets?.find((w) => w.id === editingId)

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold text-text">Analytics</h2>
        {!adding && !editingId && (
          <button
            onClick={() => setAdding(true)}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-black hover:bg-accent-hover"
          >
            + Add widget
          </button>
        )}
      </div>

      {adding && (
        <WidgetForm onCancel={() => setAdding(false)} onSaved={() => setAdding(false)} />
      )}

      {editingWidget && (
        <WidgetForm
          initial={editingWidget}
          onCancel={() => setEditingId(null)}
          onSaved={() => setEditingId(null)}
        />
      )}

      {isLoading && <p className="text-text-muted">Loading…</p>}

      {widgets && widgets.length === 0 && !adding && (
        <p className="text-text-muted">
          No widgets yet — add one to start building your own analytics.
        </p>
      )}

      {widgets && widgets.length > 0 && (
        <WidgetGrid widgets={widgets} onEdit={setEditingId} />
      )}
    </div>
  )
}
