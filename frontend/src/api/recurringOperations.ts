import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { apiClient } from './client'
import { getErrorMessage } from './errors'

export type RecurringOperationType = 'income' | 'expense' | 'fee'
export type AmountMode = 'fixed' | 'percent_of_balance'
export type RecurrenceInterval = 'daily' | 'weekly' | 'monthly' | 'yearly'

export interface RecurringOperation {
  id: number
  operation_type: RecurringOperationType
  balance_id: number
  currency_ticker: string
  amount_mode: AmountMode
  amount_value: string
  category_id: number | null
  counterparty: string | null
  note: string | null
  interval: RecurrenceInterval
  day_of_month: number | null
  day_of_week: number | null
  month: number | null
  hour: number
  minute: number
  last_run_at: string | null
  is_active: boolean
}

export interface RecurringOperationCreatePayload {
  operation_type: RecurringOperationType
  balance_id: number
  currency_ticker: string
  amount_mode: AmountMode
  amount_value: string
  category_id?: number
  counterparty?: string
  note?: string
  interval: RecurrenceInterval
  day_of_month?: number | null
  day_of_week?: number | null
  month?: number | null
  hour?: number
  minute?: number
}

export interface RecurringOperationUpdatePayload {
  // schedule fields (interval/day_of_month/day_of_week/month/hour/minute) are
  // not editable — rescheduling mid-cycle is ambiguous, so it's delete + create
  amount_mode?: AmountMode
  amount_value?: string
  category_id?: number
  counterparty?: string
  note?: string
  is_active?: boolean
}

const RECURRING_OPERATIONS_KEY = ['recurring-operations']

async function fetchRecurringOperationsByBalance(
  balanceId: number,
): Promise<RecurringOperation[]> {
  const { data } = await apiClient.get<{ items: RecurringOperation[] }>('/recurring-operations', {
    params: { balance_id: balanceId },
  })
  return data.items
}

async function createRecurringOperation(
  payload: RecurringOperationCreatePayload,
): Promise<RecurringOperation> {
  const { data } = await apiClient.post<RecurringOperation>('/recurring-operations', payload)
  return data
}

async function updateRecurringOperation(
  id: number,
  payload: RecurringOperationUpdatePayload,
): Promise<RecurringOperation> {
  const { data } = await apiClient.patch<RecurringOperation>(
    `/recurring-operations/${id}`,
    payload,
  )
  return data
}

async function deleteRecurringOperation(id: number): Promise<void> {
  await apiClient.delete(`/recurring-operations/${id}`)
}

export function useRecurringOperationsByBalance(balanceId: number) {
  return useQuery({
    queryKey: [...RECURRING_OPERATIONS_KEY, balanceId],
    queryFn: () => fetchRecurringOperationsByBalance(balanceId),
  })
}

export function useCreateRecurringOperation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createRecurringOperation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RECURRING_OPERATIONS_KEY })
      toast.success('Recurring operation created')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useUpdateRecurringOperation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: RecurringOperationUpdatePayload }) =>
      updateRecurringOperation(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RECURRING_OPERATIONS_KEY })
      toast.success('Recurring operation updated')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useDeleteRecurringOperation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteRecurringOperation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RECURRING_OPERATIONS_KEY })
      toast.success('Recurring operation deleted')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}
