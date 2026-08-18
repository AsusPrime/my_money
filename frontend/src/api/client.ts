import axios from 'axios'

function defaultApiBaseUrl(): string {
  return `http://${window.location.hostname}:8000`
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl(),
})
