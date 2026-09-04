import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ACCOUNTS_KEY } from './accounts'
import { BALANCES_KEY } from './balances'
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

export interface LedgerUpdatePayload {
  category_id?: number
  counterparty?: string
  note?: string
}

export interface LedgerPage {
  items: LedgerEntry[]
  has_more: boolean
}

const LEDGER_KEY = ['ledger']
const OPERATION_GROUP_KEY = ['ledger-operation-group']
const COUNTERPARTIES_KEY = ['counterparties']
const LEDGER_PAGE_SIZE = 30

async function fetchLedgerPage(balanceId: number, offset: number): Promise<LedgerPage> {
  const { data } = await apiClient.get<LedgerPage>(`/balances/${balanceId}/ledgers`, {
    params: { limit: LEDGER_PAGE_SIZE, offset },
  })
  return data
}

async function fetchOperationGroup(ledgerId: number): Promise<LedgerEntry[]> {
  const { data } = await apiClient.get<LedgerEntry | { items: LedgerEntry[] }>(
    `/ledger/operations/${ledgerId}/group`,
  )
  return 'items' in data ? data.items : [data]
}

async function recordOperation(payload: OperationPayload): Promise<unknown> {
  const { data } = await apiClient.post('/ledger/operations', payload)
  return data
}

async function updateLedgerEntry(id: number, payload: LedgerUpdatePayload): Promise<unknown> {
  const { data } = await apiClient.patch(`/ledger/operations/${id}`, payload)
  return data
}

async function replaceOperation(id: number, payload: OperationPayload): Promise<unknown> {
  const { data } = await apiClient.put(`/ledger/operations/${id}`, payload)
  return data
}

async function deleteOperation(id: number): Promise<void> {
  await apiClient.delete(`/ledger/operations/${id}`)
}

// reuses the existing flexible-report endpoint rather than a dedicated one —
// grouping the whole ledger by counterparty already gives exactly the
// distinct-names list a counterparty autocomplete needs
async function fetchCounterparties(): Promise<string[]> {
  const { data } = await apiClient.get<{ items: { group: string | null }[] }>('/ledger/report', {
    params: { group_by: 'counterparty', metric: 'count' },
  })
  return data.items
    .map((item) => item.group)
    .filter((name): name is string => Boolean(name) && name !== 'Unknown')
}

export function useBalanceLedger(balanceId: number) {
  return useInfiniteQuery({
    queryKey: [...LEDGER_KEY, balanceId],
    queryFn: ({ pageParam }) => fetchLedgerPage(balanceId, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) =>
      lastPage.has_more
        ? allPages.reduce((loaded, page) => loaded + page.items.length, 0)
        : undefined,
  })
}

export function useCounterparties() {
  return useQuery({ queryKey: COUNTERPARTIES_KEY, queryFn: fetchCounterparties })
}

export function useOperationGroup(ledgerId: number | null) {
  return useQuery({
    queryKey: [...OPERATION_GROUP_KEY, ledgerId],
    queryFn: () => fetchOperationGroup(ledgerId as number),
    enabled: ledgerId !== null,
  })
}

export function useRecordOperation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: recordOperation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LEDGER_KEY })
      queryClient.invalidateQueries({ queryKey: COUNTERPARTIES_KEY })
      // a new operation changes the balance's (and account's) amounts/total —
      // without this they'd stay stale until a manual page reload
      queryClient.invalidateQueries({ queryKey: BALANCES_KEY })
      queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY })
      toast.success('Operation recorded')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useUpdateLedgerEntry() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: LedgerUpdatePayload }) =>
      updateLedgerEntry(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LEDGER_KEY })
      queryClient.invalidateQueries({ queryKey: COUNTERPARTIES_KEY })
      toast.success('Ledger entry updated')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useReplaceOperation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: OperationPayload }) =>
      replaceOperation(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LEDGER_KEY })
      queryClient.invalidateQueries({ queryKey: OPERATION_GROUP_KEY })
      queryClient.invalidateQueries({ queryKey: COUNTERPARTIES_KEY })
      queryClient.invalidateQueries({ queryKey: BALANCES_KEY })
      queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY })
      toast.success('Operation updated')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useDeleteOperation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteOperation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LEDGER_KEY })
      queryClient.invalidateQueries({ queryKey: BALANCES_KEY })
      queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY })
      toast.success('Operation deleted')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}
