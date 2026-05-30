export type Urgency = 'low' | 'medium' | 'high' | 'critical'

export type Category = 'incident' | 'request' | 'admin' | 'follow-up' | 'other'

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
