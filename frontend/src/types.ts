export interface RoundTripResult {
  pivot_lang: string
  back_translation: string
}

export interface SegmentRow {
  i: number
  original: string
  back_by_pivot: Record<string, string>
  cosine_by_pivot: Record<string, number>
  surface_by_pivot: Record<string, number>
}

export interface Summary {
  mean_cosine_by_pivot: Record<string, number>
  cross_pivot_gap: number
  risk_level: string
}

export interface AnalyzeMeta {
  translator_id: string
  embedding_provider: string
  embedding_model_id: string
}

export interface AnalyzeResponse {
  original_text: string
  source_lang: string
  pivot_langs: string[]
  round_trips: RoundTripResult[]
  segments: SegmentRow[]
  summary: Summary
  meta: AnalyzeMeta
}
