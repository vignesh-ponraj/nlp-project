import { useMemo, useState } from 'react'
import type { AnalyzeResponse, SegmentRow } from './types'
import './App.css'

const MAX_CHARS = 800

const LANG_OPTIONS: { code: string; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Spanish' },
  { code: 'fr', label: 'French' },
  { code: 'de', label: 'German' },
  { code: 'it', label: 'Italian' },
  { code: 'pt', label: 'Portuguese' },
  { code: 'ja', label: 'Japanese' },
  { code: 'ko', label: 'Korean' },
  { code: 'zh-Hans', label: 'Chinese (Simplified)' },
  { code: 'ar', label: 'Arabic' },
  { code: 'hi', label: 'Hindi' },
  { code: 'ru', label: 'Russian' },
  { code: 'nl', label: 'Dutch' },
  { code: 'pl', label: 'Polish' },
  { code: 'sv', label: 'Swedish' },
]

function apiBase(): string {
  const v = import.meta.env.VITE_API_BASE as string | undefined
  if (v) return v.replace(/\/$/, '')
  return '/api'
}

function minCosine(row: SegmentRow): number {
  const vals = Object.values(row.cosine_by_pivot)
  return vals.length ? Math.min(...vals) : 0
}

function segmentHeatColor(cosine: number): string {
  const t = Math.max(0, Math.min(1, cosine))
  const hue = t * 120
  return `hsl(${hue} 70% 38%)`
}

function riskBadgeClass(level: string): string {
  if (level === 'low') return 'badge badge-low'
  if (level === 'medium') return 'badge badge-mid'
  return 'badge badge-high'
}

export default function App() {
  const [text, setText] = useState(
    'I do not think this product is terrible — it exceeded my expectations in some ways.',
  )
  const [sourceLang, setSourceLang] = useState('en')
  const [pivotA, setPivotA] = useState('es')
  const [pivotB, setPivotB] = useState('ja')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)

  const worstIndex = useMemo(() => {
    if (!result?.segments.length) return -1
    let best = 0
    let bestVal = minCosine(result.segments[0])
    result.segments.forEach((s, i) => {
      const m = minCosine(s)
      if (m < bestVal) {
        bestVal = m
        best = i
      }
    })
    return best
  }, [result])

  async function runAnalyze() {
    setError(null)
    setResult(null)
    if (!text.trim()) {
      setError('Please enter some text.')
      return
    }
    if (pivotA === pivotB) {
      setError('Choose two different pivot languages.')
      return
    }
    if (sourceLang === pivotA || sourceLang === pivotB) {
      setError('Pivot languages must differ from the source language.')
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`${apiBase()}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text.trim(),
          source_lang: sourceLang,
          pivot_langs: [pivotA, pivotB],
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        let detail: string
        if (typeof data.detail === 'string') {
          detail = data.detail
        } else if (Array.isArray(data.detail)) {
          detail = data.detail
            .map((d: { msg?: string; type?: string }) => d.msg || d.type || JSON.stringify(d))
            .join('; ')
        } else {
          detail = res.statusText
        }
        throw new Error(detail || `Request failed (${res.status})`)
      }
      setResult(data as AnalyzeResponse)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  function downloadJson() {
    if (!result) return
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'pivotdrift-result.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  async function copyJson() {
    if (!result) return
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2))
  }

  return (
    <div className="page">
      <header className="hero">
        <p className="eyebrow">Cross-lingual meaning drift</p>
        <h1>PivotDrift</h1>
        <p className="tagline">
          See how meaning shifts when your text travels through <strong>two pivot languages</strong> and
          back — with segment-level semantic and surface metrics.
        </p>
        <ul className="bullets">
          <li>Dual-pivot round-trip exposes instability a single pivot can hide.</li>
          <li>Embedding cosine + string similarity make drift inspectable.</li>
          <li>JSON API for reproducible demos and future evaluation work.</li>
        </ul>
      </header>

      <section className="panel">
        <label className="label" htmlFor="text">
          Text to analyze
        </label>
        <textarea
          id="text"
          className="textarea"
          value={text}
          maxLength={MAX_CHARS}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder="Paste a short sentence or paragraph (max 800 characters)."
        />
        <div className="char-count">
          {text.length} / {MAX_CHARS}
        </div>

        <div className="grid-3">
          <div>
            <label className="label" htmlFor="src">
              Source language
            </label>
            <select
              id="src"
              className="select"
              value={sourceLang}
              onChange={(e) => setSourceLang(e.target.value)}
            >
              {LANG_OPTIONS.map((o) => (
                <option key={o.code} value={o.code}>
                  {o.label} ({o.code})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="p1">
              Pivot A
            </label>
            <select id="p1" className="select" value={pivotA} onChange={(e) => setPivotA(e.target.value)}>
              {LANG_OPTIONS.map((o) => (
                <option key={o.code} value={o.code}>
                  {o.label} ({o.code})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="p2">
              Pivot B
            </label>
            <select id="p2" className="select" value={pivotB} onChange={(e) => setPivotB(e.target.value)}>
              {LANG_OPTIONS.map((o) => (
                <option key={o.code} value={o.code}>
                  {o.label} ({o.code})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="actions">
          <button type="button" className="btn primary" disabled={loading} onClick={runAnalyze}>
            {loading ? 'Analyzing…' : 'Analyze'}
          </button>
          {result && (
            <>
              <button type="button" className="btn" onClick={downloadJson}>
                Download JSON
              </button>
              <button type="button" className="btn" onClick={copyJson}>
                Copy JSON
              </button>
            </>
          )}
        </div>

        {error && <div className="alert error">{error}</div>}

        <p className="hint">
          Educational tool only — not for high-stakes automated decisions. Translation and embedding APIs
          introduce their own biases; interpret scores as probes, not ground truth.
        </p>
      </section>

      {result && (
        <section className="panel results">
          <h2>Results</h2>
          <div className="summary-bar">
            <div>
              <span className="muted">Cross-pivot gap (mean cosine)</span>
              <strong>{result.summary.cross_pivot_gap}</strong>
            </div>
            <div>
              <span className="muted">Risk (heuristic)</span>
              <span className={riskBadgeClass(result.summary.risk_level)}>{result.summary.risk_level}</span>
            </div>
            <div className="meta-line">
              <span className="muted">
                {result.meta.translator_id} · {result.meta.embedding_provider} / {result.meta.embedding_model_id}
              </span>
            </div>
          </div>

          <div className="means">
            {result.pivot_langs.map((p) => (
              <div key={p} className="mean-chip">
                Mean cosine ({p}): <strong>{result.summary.mean_cosine_by_pivot[p]}</strong>
              </div>
            ))}
          </div>

          <h3>Round-trip back-translations</h3>
          <div className="round-grid">
            {result.round_trips.map((rt) => (
              <article key={rt.pivot_lang} className="card">
                <h4>Via {rt.pivot_lang}</h4>
                <p className="back-text">{rt.back_translation}</p>
              </article>
            ))}
          </div>

          <h3>Segment drift map</h3>
          <p className="muted small">
            Row color reflects the minimum cosine similarity to the original across pivots (greener = closer).
            The weakest row is outlined.
          </p>
          <div className="table-wrap">
            <table className="drift-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Original</th>
                  {result.pivot_langs.map((p) => (
                    <th key={p}>Back ({p})</th>
                  ))}
                  {result.pivot_langs.map((p) => (
                    <th key={`c-${p}`}>Cos ({p})</th>
                  ))}
                  {result.pivot_langs.map((p) => (
                    <th key={`s-${p}`}>Surface ({p})</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.segments.map((row) => {
                  const mc = minCosine(row)
                  const weak = row.i === worstIndex
                  return (
                    <tr
                      key={row.i}
                      className={weak ? 'row-weak' : ''}
                      style={{ backgroundColor: segmentHeatColor(mc) }}
                    >
                      <td>{row.i}</td>
                      <td className="cell-text">{row.original}</td>
                      {result.pivot_langs.map((p) => (
                        <td key={p} className="cell-text">
                          {row.back_by_pivot[p]}
                        </td>
                      ))}
                      {result.pivot_langs.map((p) => (
                        <td key={`c-${p}`}>{row.cosine_by_pivot[p]}</td>
                      ))}
                      {result.pivot_langs.map((p) => (
                        <td key={`s-${p}`}>{row.surface_by_pivot[p]}</td>
                      ))}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
