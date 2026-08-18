import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'

export interface Currency {
  ticker: string
  name: string | null
  currency_type: 'fiat' | 'bond' | 'stock' | 'crypto' | 'other'
}

async function fetchCurrencies(): Promise<Currency[]> {
  const { data } = await apiClient.get<{ items: Currency[] }>('/currencies')
  return data.items
}

export function useCurrencies() {
  return useQuery({ queryKey: ['currencies'], queryFn: fetchCurrencies })
}
