import { AxiosError } from 'axios'

export function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (error.message) return error.message
  }
  if (error instanceof Error) return error.message
  return 'Unexpected error'
}
