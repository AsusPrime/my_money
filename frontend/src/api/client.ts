import axios from 'axios'

function defaultApiBaseUrl(): string {
  return `http://${window.location.hostname}:8000`
}

// axios's default params serializer encodes array values as `key[]=a&key[]=b`,
// but FastAPI's `list[...] = Query(None)` params only match the exact
// repeated-key form `key=a&key=b` (no brackets) — without this, any array
// filter (operation_types, category_ids, balance_ids, ...) would silently
// match nothing server-side.
function serializeParams(params: Record<string, unknown>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) return
    if (Array.isArray(value)) {
      value.forEach((item) => search.append(key, String(item)))
    } else {
      search.append(key, String(value))
    }
  })
  return search.toString()
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl(),
  paramsSerializer: { serialize: serializeParams },
})
