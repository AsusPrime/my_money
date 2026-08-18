import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { apiClient } from './client'
import { getErrorMessage } from './errors'

export interface Account {
  id: number
  name: string
  base_currency_ticker: string
  is_archived: boolean
  created_at: string
}

export interface AccountCreatePayload {
  name: string
  base_currency_ticker: string
}

export interface AccountUpdatePayload {
  name?: string
  base_currency_ticker?: string
}

const ACCOUNTS_KEY = ['accounts']

export async function fetchAccounts(): Promise<Account[]> {
  const { data } = await apiClient.get<{ items: Account[] }>('/accounts')
  return data.items
}

async function createAccount(payload: AccountCreatePayload): Promise<Account> {
  const { data } = await apiClient.post<Account>('/accounts', payload)
  return data
}

async function updateAccount(id: number, payload: AccountUpdatePayload): Promise<Account> {
  const { data } = await apiClient.patch<Account>(`/accounts/${id}`, payload)
  return data
}

async function archiveAccount(id: number): Promise<void> {
  await apiClient.post(`/accounts/${id}/archive`)
}

export function useAccounts() {
  return useQuery({ queryKey: ACCOUNTS_KEY, queryFn: fetchAccounts })
}

export function useCreateAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAccount,
    onSuccess: (account) => {
      queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY })
      toast.success(`Account "${account.name}" created`)
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useUpdateAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: AccountUpdatePayload }) =>
      updateAccount(id, payload),
    onSuccess: (account) => {
      queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY })
      toast.success(`Account "${account.name}" updated`)
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useArchiveAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: archiveAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY })
      toast.success('Account archived')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}
