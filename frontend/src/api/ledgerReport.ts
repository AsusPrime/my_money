import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'

export const LEDGER_REPORT_GROUP_BY_OPTIONS = [
  'category',
  'counterparty',
  'operation_type',
  'currency_ticker',
  'balance',
  'account',
  'day',
  'week',
  'month',
  'quarter',
  'year',
] as const
export type LedgerReportGroupBy = (typeof LEDGER_REPORT_GROUP_BY_OPTIONS)[number]

export const LEDGER_REPORT_METRIC_OPTIONS = ['sum', 'count', 'net_of_fees'] as const
export type LedgerReportMetric = (typeof LEDGER_REPORT_METRIC_OPTIONS)[number]

export interface LedgerReportItem {
  group: string | null
  value: string
}

export interface LedgerReportParams {
  group_by: LedgerReportGroupBy
  metric: LedgerReportMetric
  date_start?: string
  date_end?: string
  operation_type?: string
  currency_ticker?: string
  category_id?: number
  balance_id?: number
  account_id?: number
}

async function fetchLedgerReport(params: LedgerReportParams): Promise<LedgerReportItem[]> {
  const { data } = await apiClient.get<{ items: LedgerReportItem[] }>('/ledger/report', {
    params,
  })
  return data.items
}

export function useLedgerReport(params: LedgerReportParams) {
  return useQuery({
    queryKey: ['ledger-report', params],
    queryFn: () => fetchLedgerReport(params),
  })
}
