import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { apiClient } from './client'
import { getErrorMessage } from './errors'

export interface BalanceGroup {
  id: number
  name: string
  account_id: number
}

export interface BalanceGroupCreatePayload {
  name: string
  account_id: number
}

export interface BalanceGroupUpdatePayload {
  name?: string
}

const BALANCE_GROUPS_KEY = ['balance-groups']

async function fetchBalanceGroups(accountId: number): Promise<BalanceGroup[]> {
  const { data } = await apiClient.get<{ items: BalanceGroup[] }>('/balance-groups', {
    params: { account_id: accountId },
  })
  return data.items
}

async function createBalanceGroup(payload: BalanceGroupCreatePayload): Promise<BalanceGroup> {
  const { data } = await apiClient.post<BalanceGroup>('/balance-groups', payload)
  return data
}

async function updateBalanceGroup(
  id: number,
  payload: BalanceGroupUpdatePayload,
): Promise<BalanceGroup> {
  const { data } = await apiClient.patch<BalanceGroup>(`/balance-groups/${id}`, payload)
  return data
}

async function deleteBalanceGroup(id: number): Promise<void> {
  await apiClient.delete(`/balance-groups/${id}`)
}

export function useBalanceGroups(accountId: number | null) {
  return useQuery({
    queryKey: [...BALANCE_GROUPS_KEY, accountId],
    queryFn: () => fetchBalanceGroups(accountId as number),
    enabled: accountId !== null,
  })
}

export function useCreateBalanceGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createBalanceGroup,
    onSuccess: (group) => {
      queryClient.invalidateQueries({ queryKey: BALANCE_GROUPS_KEY })
      toast.success(`Group "${group.name}" created`)
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useUpdateBalanceGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: BalanceGroupUpdatePayload }) =>
      updateBalanceGroup(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BALANCE_GROUPS_KEY })
      toast.success('Group renamed')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useDeleteBalanceGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteBalanceGroup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BALANCE_GROUPS_KEY })
      // balances in the deleted group aren't deleted — they just lose their
      // group_id (backend FK is ON DELETE SET NULL), so refresh those too
      queryClient.invalidateQueries({ queryKey: ['balances'] })
      toast.success('Group deleted')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}
