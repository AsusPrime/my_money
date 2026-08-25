import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { apiClient } from './client'
import { getErrorMessage } from './errors'

export type CurrencyType = 'fiat' | 'bond' | 'stock' | 'crypto' | 'other'

export interface Currency {
  ticker: string
  name: string | null
  currency_type: CurrencyType
}

export interface CurrencyCreatePayload {
  ticker: string
  currency_type: CurrencyType
  name?: string
}

const CURRENCIES_KEY = ['currencies']

async function fetchCurrencies(): Promise<Currency[]> {
  const { data } = await apiClient.get<{ items: Currency[] }>('/currencies')
  return data.items
}

async function createCurrency(payload: CurrencyCreatePayload): Promise<Currency> {
  const { data } = await apiClient.post<Currency>('/currencies', payload)
  return data
}

export function useCurrencies() {
  return useQuery({ queryKey: CURRENCIES_KEY, queryFn: fetchCurrencies })
}

export function useCreateCurrency() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCurrency,
    onSuccess: (currency) => {
      queryClient.invalidateQueries({ queryKey: CURRENCIES_KEY })
      toast.success(`Currency "${currency.ticker}" added`)
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}
