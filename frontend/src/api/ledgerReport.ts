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

export const NET_WORTH_BUCKET_OPTIONS = ['day', 'week', 'month', 'quarter', 'year'] as const
export type NetWorthBucket = (typeof NET_WORTH_BUCKET_OPTIONS)[number]

export const LEDGER_REPORT_METRIC_OPTIONS = [
  'sum',
  'count',
  'net_of_fees',
  // not sent to /ledger/report — a widget with this metric is rendered via
  // useNetWorthReport (/ledger/net-worth) instead, see AnalyticsPage
  'net_worth',
] as const
export type LedgerReportMetric = (typeof LEDGER_REPORT_METRIC_OPTIONS)[number]

export interface LedgerReportItem {
  group: string | null
  value: string
}

export interface LedgerReportParams {
  group_by: LedgerReportGroupBy
  metric: Exclude<LedgerReportMetric, 'net_worth'>
  date_start?: string
  date_end?: string
  operation_types?: string[]
  currency_ticker?: string
  category_ids?: number[]
  balance_ids?: number[]
  account_id?: number
}

export interface NetWorthParams {
  currency_ticker: string
  group_by: NetWorthBucket
  date_start?: string
  date_end?: string
  account_id?: number
  balance_ids?: number[]
}

async function fetchLedgerReport(params: LedgerReportParams): Promise<LedgerReportItem[]> {
  const { data } = await apiClient.get<{ items: LedgerReportItem[] }>('/ledger/report', {
    params,
  })
  return data.items
}

export function useLedgerReport(params: LedgerReportParams, enabled = true) {
  return useQuery({
    queryKey: ['ledger-report', params],
    queryFn: () => fetchLedgerReport(params),
    enabled,
  })
}

async function fetchNetWorth(params: NetWorthParams): Promise<LedgerReportItem[]> {
  const { data } = await apiClient.get<{ items: LedgerReportItem[] }>('/ledger/net-worth', {
    params,
  })
  return data.items
}

export function useNetWorthReport(params: NetWorthParams, enabled = true) {
  return useQuery({
    queryKey: ['net-worth', params],
    queryFn: () => fetchNetWorth(params),
    enabled: enabled && Boolean(params.currency_ticker),
  })
}
