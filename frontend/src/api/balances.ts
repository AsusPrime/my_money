import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { apiClient } from './client'
import { getErrorMessage } from './errors'
import { fetchAccounts } from './accounts'

export interface Balance {
  id: number
  name: string
  account_id: number
  is_archived: boolean
  created_at: string
}

export interface BalanceCreatePayload {
  name: string
  account_id: number
}

const BALANCES_KEY = ['balances']
const ALL_BALANCES_KEY = ['balances', 'all']

async function fetchBalancesByAccount(accountId: number): Promise<Balance[]> {
  const { data } = await apiClient.get<{ items: Balance[] }>('/balances', {
    params: { account_id: accountId },
  })
  return data.items
}

async function fetchAllBalances(): Promise<Balance[]> {
  const accounts = await fetchAccounts()
  const activeAccounts = accounts.filter((account) => !account.is_archived)
  const perAccount = await Promise.all(
    activeAccounts.map((account) => fetchBalancesByAccount(account.id)),
  )
  return perAccount.flat().filter((balance) => !balance.is_archived)
}

async function createBalance(payload: BalanceCreatePayload): Promise<Balance> {
  const { data } = await apiClient.post<Balance>('/balances', payload)
  return data
}

async function archiveBalance(balanceId: number): Promise<void> {
  await apiClient.post(`/balances/${balanceId}/archive`)
}

async function fetchBalanceAmounts(balanceId: number): Promise<Record<string, string>> {
  const { data } = await apiClient.get<{ amounts: Record<string, string> }>(
    `/balances/${balanceId}/amounts`,
  )
  return data.amounts
}

export function useBalances(accountId: number | null) {
  return useQuery({
    queryKey: [...BALANCES_KEY, accountId],
    queryFn: () => fetchBalancesByAccount(accountId!),
    enabled: accountId !== null,
  })
}

export function useAllBalances() {
  return useQuery({ queryKey: ALL_BALANCES_KEY, queryFn: fetchAllBalances })
}

export function useBalanceAmounts(balanceId: number) {
  return useQuery({
    queryKey: [...BALANCES_KEY, balanceId, 'amounts'],
    queryFn: () => fetchBalanceAmounts(balanceId),
  })
}

export function useCreateBalance() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createBalance,
    onSuccess: (balance) => {
      queryClient.invalidateQueries({ queryKey: BALANCES_KEY })
      toast.success(`Balance "${balance.name}" created`)
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useArchiveBalance() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: archiveBalance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BALANCES_KEY })
      toast.success('Balance archived')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}
