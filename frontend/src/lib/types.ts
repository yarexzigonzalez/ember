export const STATUSES = [
  { id: 'saved', label: 'Saved' },
  { id: 'applied', label: 'Applied' },
  { id: 'oa', label: 'OA' },
  { id: 'interview', label: 'Interview' },
  { id: 'offer', label: 'Offer' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'ghosted', label: 'Ghosted' },
] as const

export type Status = (typeof STATUSES)[number]['id']

export const SOURCES = [
  'LinkedIn',
  'Handshake',
  'Referral',
  'Company site',
  'Other',
] as const

export const ROLE_TYPES = [
  { id: 'intern', label: 'Intern' },
  { id: 'full_time', label: 'Full-time' },
  { id: 'contract', label: 'Contract' },
  { id: 'unknown', label: 'Not sure' },
] as const

export const SENIORITY = [
  { id: 'intern', label: 'Intern' },
  { id: 'new_grad', label: 'New grad' },
  { id: 'junior', label: 'Junior' },
  { id: 'mid', label: 'Mid' },
  { id: 'senior', label: 'Senior' },
  { id: 'unknown', label: 'Not sure' },
] as const

export type User = {
  id: string
  email: string
  display_name: string | null
  timezone: string
  is_demo: boolean
  weekly_goal: number
  ghost_after_days: number
  created_at: string
}

export type Application = {
  id: string
  company: string
  role: string
  location: string | null
  source: string | null
  posting_url: string | null
  status: Status
  seniority: string | null
  role_type: string | null
  requirements: string[]
  notes: string | null
  applied_at: string | null
  last_status_at: string
  created_at: string
  updated_at: string
}

export type ApplicationList = {
  items: Application[]
  total: number
  page: number
  page_size: number
}

export type ApplicationInput = {
  company: string
  role: string
  location?: string | null
  source?: string | null
  posting_url?: string | null
  status?: Status
  seniority?: string | null
  role_type?: string | null
  requirements?: string[]
  notes?: string | null
  applied_at?: string | null
}
