export type Urgency = 'low' | 'medium' | 'high' | 'critical'

export type Category = 'incident' | 'request' | 'admin' | 'follow_up' | 'other'

export type Sentiment = 'negative' | 'neutral' | 'positive'

export interface TriageRecord {
  id: string
  subject_or_title?: string
  urgency: Urgency
  urgency_reason: string
  category: Category
  category_reason: string
  sentiment: Sentiment
  sentiment_reason: string
  /** True when a human correction overlay is applied (GET /triage). */
  corrected?: boolean
}

export interface ApiError {
  status: number
  message: string
}

export interface BriefingMetrics {
  totalWorkItems: string
  urgencyMix: string
  sentimentMix: string
}

export interface ParsedBriefing {
  title: string
  metrics: BriefingMetrics
  topPriorities: string[]
  dueSoon: string[]
  rawText: string
}

export interface RunArtifacts {
  triage_results?: string
  action_items?: string
  suggested_responses?: string
  daily_briefing?: string
}

export interface RunSummary {
  run_id: string
  started_at?: string
  finished_at?: string
  duration_ms?: number
  status?: string
  item_count?: number
  triage_count?: number
  action_count?: number
  suggested_response_count?: number
  artifacts?: RunArtifacts
  error?: string | null
}

export type RunMetadata = RunSummary

export interface RunPipelineResult {
  status: string
  stdout: string
}

export interface AskRequest {
  question: string
  assistant_name: string
}

export interface AskResponse {
  answer: string
}

export interface AskMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  timestamp: number
}

export interface AskToolStep {
  id: string
  tool: string
  status: 'running' | 'done' | 'error'
}

export interface AskDraftCard {
  draftId: string
  subject: string
  body: string
  toAddrs: string
  sentAt?: number | null
  approveError?: string | null
  idempotencyKey?: string
  approving?: boolean
  /** Last approve settled as ambiguous send; show deliberate re-send label. */
  sendOutcomeUnknown?: boolean
  /** True when the draft can be re-created after a send failure. */
  reopenable?: boolean
  /** True while a reopen request is in flight. */
  reopening?: boolean
}

export interface EveningSummaryRequest {
  assistant_name: string
}

export interface EveningSummaryResponse {
  summary: string
}

export interface InsightItem {
  title: string
  body: string
  category: string
}

export interface InsightsResponse {
  intro: string
  insights: InsightItem[]
}

export interface Capability {
  id: string
  name: string
  category: string
  apps: string[]
  status: 'connected' | 'available' | 'coming_soon'
  featured: boolean
  description: string
}

export type AIProvider = 'anthropic'

export interface CalendarMeeting {
  id: string
  provider_id: string
  title: string
  start_at: string
  end_at: string
}

export interface SyncResult {
  /** Drain outcome: not_needed | started | busy */
  drain: 'not_needed' | 'started' | 'busy'
  job_id?: string | null
  account_email: string
  gmail_upserted: number
  gmail_removed?: number
  calendar_upserted: number
  gmail_total?: number
  meetings_total?: number
  triaged: number
  pending: number
  /** True when calendar list hit max pages (C2). */
  calendar_truncated?: boolean
  /** True when Gmail full-list hit max pages (C3/A5). */
  gmail_truncated?: boolean
}

export interface JobStatus {
  id: string
  job_kind: string
  status: string
  triaged: number
  pending: number
  error_code?: string | null
  run_id?: string | null
  created_at: string
  started_at?: string | null
  finished_at?: string | null
}

export interface JobStatusSummary {
  id: string
  status: string
  triaged: number
  pending: number
  error_code?: string | null
  finished_at?: string | null
}

export interface ApiSettings {
  provider: string
  model: string
  api_key_set: boolean
  demo_mode?: boolean
  google_connected?: boolean
  last_morning?: JobStatusSummary | null
  last_sync?: JobStatusSummary | null
}

export interface CorrectionPayload {
  urgency: Urgency
  category: Category
  sentiment: Sentiment
}
