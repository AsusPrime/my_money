import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { apiClient } from './client'
import { getErrorMessage } from './errors'
import type { LedgerReportGroupBy, LedgerReportMetric } from './ledgerReport'

export const CHART_TYPE_OPTIONS = ['bar', 'pie', 'line'] as const
export type ChartType = (typeof CHART_TYPE_OPTIONS)[number]

export const DATE_RANGE_PRESET_OPTIONS = [
  'all',
  'this_month',
  'last_month',
  'last_7_days',
  'last_30_days',
  'this_year',
  'custom',
] as const
export type DateRangePreset = (typeof DATE_RANGE_PRESET_OPTIONS)[number]

export interface AnalyticsWidgetFilters {
  date_range_preset?: DateRangePreset | null
  date_start?: string | null
  date_end?: string | null
  operation_types?: string[] | null
  currency_ticker?: string | null
  category_ids?: number[] | null
  balance_ids?: number[] | null
  account_id?: number | null
}

export interface AnalyticsWidget {
  id: number
  title: string
  chart_type: ChartType
  group_by: LedgerReportGroupBy
  metric: LedgerReportMetric
  filters: AnalyticsWidgetFilters
  grid_x: number
  grid_y: number
  grid_w: number
  grid_h: number
}

export interface AnalyticsWidgetLayoutItem {
  id: number
  x: number
  y: number
  w: number
  h: number
}

export interface AnalyticsWidgetPayload {
  title: string
  chart_type: ChartType
  group_by: LedgerReportGroupBy
  metric: LedgerReportMetric
  filters: AnalyticsWidgetFilters
}

const ANALYTICS_WIDGETS_KEY = ['analytics-widgets']

async function fetchAnalyticsWidgets(): Promise<AnalyticsWidget[]> {
  const { data } = await apiClient.get<{ items: AnalyticsWidget[] }>('/analytics/widgets')
  return data.items
}

async function createAnalyticsWidget(
  payload: AnalyticsWidgetPayload,
): Promise<AnalyticsWidget> {
  const { data } = await apiClient.post<AnalyticsWidget>('/analytics/widgets', payload)
  return data
}

async function updateAnalyticsWidget(
  id: number,
  payload: AnalyticsWidgetPayload,
): Promise<AnalyticsWidget> {
  const { data } = await apiClient.patch<AnalyticsWidget>(`/analytics/widgets/${id}`, payload)
  return data
}

async function deleteAnalyticsWidget(id: number): Promise<void> {
  await apiClient.delete(`/analytics/widgets/${id}`)
}

async function updateAnalyticsWidgetsLayout(
  items: AnalyticsWidgetLayoutItem[],
): Promise<AnalyticsWidget[]> {
  const { data } = await apiClient.patch<{ items: AnalyticsWidget[] }>(
    '/analytics/widgets/layout',
    { items },
  )
  return data.items
}

export function useAnalyticsWidgets() {
  return useQuery({
    queryKey: ANALYTICS_WIDGETS_KEY,
    queryFn: fetchAnalyticsWidgets,
  })
}

export function useCreateAnalyticsWidget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAnalyticsWidget,
    onSuccess: (widget) => {
      queryClient.invalidateQueries({ queryKey: ANALYTICS_WIDGETS_KEY })
      toast.success(`Widget "${widget.title}" added`)
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useUpdateAnalyticsWidget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: AnalyticsWidgetPayload }) =>
      updateAnalyticsWidget(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ANALYTICS_WIDGETS_KEY })
      toast.success('Widget updated')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useDeleteAnalyticsWidget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteAnalyticsWidget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ANALYTICS_WIDGETS_KEY })
      toast.success('Widget removed')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useUpdateAnalyticsWidgetsLayout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateAnalyticsWidgetsLayout,
    onSuccess: (items) => {
      queryClient.setQueryData(ANALYTICS_WIDGETS_KEY, items)
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}
