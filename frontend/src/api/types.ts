export type Urgency = 'low' | 'medium' | 'high' | 'critical'

export type Category = 'incident' | 'request' | 'admin' | 'follow_up' | 'other'

export type Sentiment = 'negative' | 'neutral' | 'positive'

export interface TriageRecord {
  id: string
  urgency: Urgency
  urgency_reason: string
  category: Category
  category_reason: string
  sentiment: Sentiment
  sentiment_reason: string
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
