export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// Always relative. Vite (dev) and Vercel (prod) forward /api to the backend,
// so the session cookie stays first-party.
const BASE = '/api'

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  const isForm = init?.body instanceof FormData
  if (init?.body && !isForm && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
    credentials: 'same-origin',
  })
  if (response.status === 204) return undefined as T
  const text = await response.text()
  let data: { detail?: unknown } | null = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = null
  }
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(response.status, data?.detail))
  }
  return data as T
}

function errorMessage(status: number, detail: unknown): string {
  if (typeof detail === 'string') return detail
  // FastAPI validation errors come back as a list of {loc, msg}
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
  if (status === 429) return 'Slow down a sec, too many tries'
  if (status >= 500) return 'Server had a moment. Try again.'
  return 'Something went wrong'
}
