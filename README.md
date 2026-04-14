# PivotDrift

**Cross-lingual meaning drift** — measure how much a short text changes when it is translated through **two different pivot languages** and back to the source language, with **segment-level** semantic (embedding cosine) and **surface** (normalized edit distance) metrics.

## What it does

1. You provide **source text** (up to 800 characters by default), a **source language** code, and **exactly two pivot** language codes.
2. The backend calls **OpenAI Chat Completions** or **Anthropic Claude (Messages API)** twice per pivot: `source → pivot → source`, producing two **back-translations** (LLM translation, not a dedicated MT API).
3. Text is **split into segments** (sentences when possible; otherwise fixed windows). If segment counts disagree after round-trip, the pipeline **falls back** to a single segment for the whole text (see Limitations).
4. For each segment, the service computes:
   - **Cosine similarity** between embeddings of the original segment and each back-translated segment (same embedding model for both).
   - **Surface similarity** = \(1 - \text{Levenshtein} / \max(\text{len}))\), a simple string-level proxy.
5. **Summary statistics** include mean cosine per pivot and **cross-pivot gap** (absolute difference of those means), plus a coarse **risk** label (`low` / `medium` / `high`) from heuristic thresholds.

**Example intuition:** Negation, idioms, intensifiers, and culturally loaded wording often show **lower cosine** or **larger disagreement between pivots** than plain factual sentences — making failures of “translation as a lossless codec” visible.

## Why it exists

Multilingual pipelines (MT, cross-lingual retrieval, localized moderation) often assume **semantic preservation** under translation. In practice, **round-trip error** is **language-pair-dependent** and **non-deterministic** in aggregate. PivotDrift is a small **analysis probe**: it does not train models; it **surfaces instability** you can discuss, screenshot, or export as JSON for qualitative research.

## Architecture

- **Backend:** Python [FastAPI](https://fastapi.tiangolo.com/) — `POST /analyze`, `GET /health`, OpenAPI at `/docs`.
- **Translation:** Configurable **OpenAI** (`/v1/chat/completions`) or **Anthropic** (`/v1/messages`) — uses your existing API subscription; no Azure or Google Cloud Translation required.
- **Embeddings:** Configurable **OpenAI** (`text-embedding-3-small` by default) or **Google Gemini** (`text-embedding-004`) via `EMBEDDING_PROVIDER` — cloud only.
- **Frontend:** [Vite](https://vitejs.dev/) + [React](https://react.dev/) (TypeScript) — single-page UI, dark theme, JSON export.

```mermaid
flowchart LR
  subgraph ui [Browser]
    SPA[Vite_React]
  end
  subgraph api [FastAPI]
    A[analyze_pipeline]
  end
  subgraph cloud [Hosted_APIs]
    T[OpenAI_or_Anthropic]
    E[Embedding_API]
  end
  SPA -->|POST_/analyze| A
  A --> T
  A --> E
```

## Tech stack

| Component   | Notes |
|------------|--------|
| Python     | 3.10+ recommended (Dockerfile uses 3.11) |
| Node.js    | 20+ for Vite 8 |
| Translation | OpenAI API key (`TRANSLATION_PROVIDER=openai`) **or** Anthropic API key (`anthropic`) |
| Embeddings | OpenAI API key **or** Google AI Studio key (`EMBEDDING_PROVIDER=gemini`) |

**Pricing:** Usage follows your **OpenAI** and **Anthropic** plan pricing for chat and embeddings. This project targets **low traffic** demos; each analyze runs several chat calls (four translation steps per request) plus embedding calls.

## Quickstart (local)

### 1. Clone and configure the API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env: set TRANSLATION_PROVIDER (openai or anthropic), matching API keys, and EMBEDDING_PROVIDER + keys (OpenAI or Gemini)
```

### 2. Run the API

From the `backend` directory (so `app` resolves and `.env` is found):

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies **`/api` → `http://127.0.0.1:8000`**, so the UI calls `/analyze` as `/api/analyze` with no extra config.

### 4. Sample `curl`

```bash
curl -s -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"I do not think this is terrible.","source_lang":"en","pivot_langs":["es","ja"]}' | jq .
```

### 5. Tests (no API keys)

```bash
cd backend
pytest -q
```

Example prompts for manual exploration live in [`backend/examples.json`](backend/examples.json).

## Configuration

| Variable | Purpose |
|----------|---------|
| `TRANSLATION_PROVIDER` | `openai` (default) or `anthropic` |
| `OPENAI_TRANSLATION_MODEL` | Chat model for translation when using OpenAI (default `gpt-4o-mini`) |
| `OPENAI_API_KEY` | Required for OpenAI translation and/or OpenAI embeddings |
| `OPENAI_BASE_URL` | Default `https://api.openai.com/v1` |
| `ANTHROPIC_API_KEY` | Required when `TRANSLATION_PROVIDER=anthropic` |
| `ANTHROPIC_TRANSLATION_MODEL` | Claude model id (default `claude-3-5-haiku-20241022`; override with your account’s available models) |
| `EMBEDDING_PROVIDER` | `openai` (default) or `gemini` |
| `OPENAI_EMBEDDING_MODEL` | Default `text-embedding-3-small` |
| `GEMINI_API_KEY` | Required if `EMBEDDING_PROVIDER=gemini` |
| `GEMINI_EMBEDDING_MODEL` | Default `text-embedding-004` |
| `FRONTEND_ORIGINS` | Comma-separated CORS origins for production |
| `MAX_INPUT_CHARS` | Max input length (default `800`) |

**Language codes** are the same BCP-47 / ISO-style tags as in the UI (e.g. `en`, `es`, `ja`, `zh-Hans`). The backend maps common codes to English names in the prompt; uncommon codes are passed through as-is for the model to interpret.

## API reference

### `POST /analyze`

**Request body**

```json
{
  "text": "Your short text.",
  "source_lang": "en",
  "pivot_langs": ["es", "ja"]
}
```

**Response (conceptual)**

- `round_trips`: back-translation string for each pivot.
- `segments[]`: per-segment original text, back-translations per pivot, `cosine_by_pivot`, `surface_by_pivot`.
- `summary`: `mean_cosine_by_pivot`, `cross_pivot_gap`, `risk_level`.
- `meta`: `translator_id`, `embedding_provider`, `embedding_model_id` for reproducibility.

Interactive schema: run the API and open **`http://127.0.0.1:8000/docs`**.

### `GET /health`

Returns `{ "status": "ok" }` for load balancers.

## Limitations (read before citing this in applications)

- **Not ground truth:** Cosine on API embeddings is a **probe**, not an objective semantics metric. Different embedding models yield different numbers.
- **Translator bias:** All legs use **one** LLM translation stack (OpenAI or Anthropic); outputs can vary between calls and share provider-specific biases.
- **Alignment:** v1 uses **ordered segment alignment**; when sentence counts diverge after round-trip, the service **collapses** to one segment — fine for demos, weak for long heterogeneous documents.
- **Length:** Designed for **short** user text; very long inputs are out of scope.
- **Risk label:** `low` / `medium` / `high` is a **heuristic** for UI affordance only.

## Ethics / misuse

PivotDrift is an **educational and analysis** tool. Do **not** use it as the sole basis for **employment, moderation, legal, or safety** decisions. Do not submit **sensitive personal data** you are not allowed to send to third-party APIs.

## Deployment (free-tier friendly)

**Backend**

- Build context directory: `backend/` (contains `Dockerfile` and `app/`).
- Example platforms: [Render](https://render.com/) (Docker Web Service), [Fly.io](https://fly.io/), [Railway](https://railway.app/).
- Set the same environment variables as in `.env.example`.
- Set `FRONTEND_ORIGINS` to your real site origin (comma-separated).

**Frontend**

- [Vercel](https://vercel.com/) or [Cloudflare Pages](https://pages.cloudflare.com/): root `frontend/`, build `npm run build`, output `dist`.
- Set **`VITE_API_BASE`** to the public API origin (e.g. `https://your-api.onrender.com`) **without** a trailing slash. The UI will call `${VITE_API_BASE}/analyze`.

**CORS:** The API only allows origins listed in `FRONTEND_ORIGINS`.

## Next improvements planned

- **Task-aware lexical flags:** small curated lexicons (negation, intensifiers, sentiment-laden words) plus character-diff windows to flag segments where polarity might have shifted across round-trip.
- **Optional bounded LLM explanations:** a single structured call to explain **top-k** flagged segments, explicitly framed as **hypotheses for human review** (not authoritative labels).
- **Third pivot or second translator** in the UI for ablation-style comparison.
- **Batch endpoint** or CSV upload for small curated evaluation sets.

---

**Tagline:** *See how meaning shifts when your text travels through two languages and back.*

**Demo:** Paste a short sentence, pick two pivots, and inspect where embeddings and surface metrics diverge — export JSON for notebooks or appendices.
