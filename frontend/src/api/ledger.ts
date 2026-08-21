import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { apiClient } from './client'
import { getErrorMessage } from './errors'

export interface LedgerEntry {
  id: number
  operation_id: string | null
  balance_id: number
  currency_ticker: string
  amount: string
  operation_type: string
  category_id: number | null
  counterparty: string | null
  note: string | null
  executed_at: string
  base_currency_rate: string | null
}

interface FeeLegFields {
  note?: string
  fee_amount?: string
  fee_currency_ticker?: string
}

export interface SingleLegPayload {
  operation_type: 'income' | 'expense' | 'fee'
  balance_id: number
  amount: string
  currency_ticker: string
  category_id?: number
  counterparty?: string
  note?: string
  executed_at?: string
  base_currency_rate?: string
}

export interface TransferPayload extends FeeLegFields {
  operation_type: 'transfer'
  from_balance_id: number
  to_balance_id: number
  amount: string
  received_amount?: string
  currency_ticker: string
  received_currency_ticker?: string
  executed_at?: string
  base_currency_rate?: string
}

export interface TradePayload extends FeeLegFields {
  operation_type: 'trade'
  balance_id: number
  spend_amount: string
  spend_currency_ticker: string
  receive_amount: string
  receive_currency_ticker: string
  executed_at?: string
  base_currency_rate?: string
}

export type OperationPayload = SingleLegPayload | TransferPayload | TradePayload

const LEDGER_KEY = ['ledger']

async function fetchLedgerByBalance(balanceId: number): Promise<LedgerEntry[]> {
  const { data } = await apiClient.get<{ items: LedgerEntry[] }>(
    `/balances/${balanceId}/ledgers`,
  )
  return data.items
}

async function recordOperation(payload: OperationPayload): Promise<unknown> {
  const { data } = await apiClient.post('/ledger/operations', payload)
  return data
}

export function useBalanceLedger(balanceId: number) {
  return useQuery({
    queryKey: [...LEDGER_KEY, balanceId],
    queryFn: () => fetchLedgerByBalance(balanceId),
  })
}

export function useRecordOperation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: recordOperation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LEDGER_KEY })
      toast.success('Operation recorded')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}
