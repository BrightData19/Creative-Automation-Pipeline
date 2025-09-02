Creative Automation Pipeline Worker
===================================

Purpose
- Consumes campaign briefs and generates creative assets.
- Uses GenAI providers (Gemini, Firefly, OpenAI) with intelligent fallback.
- Performs brand compliance and legal checks.
- Produces variants in 1:1, 16:9, and 9:16 aspect ratios.
 - Ingests mixed assets (images, videos, audio, docs, presentations, graphics) from an inbox folder. Reuses images when available; otherwise generates a new base image (single high-res call, then resizes).
 - Saves generated and transient artifacts (prompts/messages, carousels, animated GIFs, catalog) to Dropbox/local storage.

Run (Local, No Kafka/Dropbox)
- Requirements: Python 3.11+, uv, Pillow, OpenCV (managed via `uv sync`).
- Steps:
  1. Create `.env` from project root `.env.example` if needed.
  2. Run with local storage backend:

     uv run python cli.py --brief ../../data/samples/brief_sample.json --storage-backend local --local-root ./local_storage

  3. Outputs saved under `local_storage/outputs/<campaign>/` with filenames containing product and ratio.

Run (Full Stack)
- Start Kafka/Redpanda and services via project Makefile. In separate terminals:
  - Frontend: `pnpm dev`
  - Realtime gateway: `pnpm dev`
  - Pipeline worker: `uv run python main.py`
  - Agent worker: `uv run python ../agent-worker/agent_graph.py`

Input Brief (JSON)
- Example: `data/samples/brief_sample.json`
- Required fields: `campaign_name`, `target_market`, `target_audience`, `campaign_message`, `products` (≥2)
- Optional: `brand_name`, `logo_path`, `inbox_folder`

Storage Backends
- Dropbox (default): set `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN`; `STORAGE_BACKEND=dropbox`
- Local (for PoC): `STORAGE_BACKEND=local`, `LOCAL_ROOT=local_storage`

GenAI Providers
- Configure keys in `.env`:
  - `GOOGLE_GEMINI_API_KEY`
  - `ADOBE_FIREFLY_CLIENT_ID`, `ADOBE_FIREFLY_CLIENT_SECRET`
  - `OPENAI_API_KEY`
- Fallback to `stub` if none set.

Brand & Legal Compliance
- Logo presence heuristic, brand color alignment, prohibited words/symbols, image content checks.
- Results emitted to Kafka in full-stack runs; printed in CLI runs.

Ingestion & Outputs
- Inbox ingestion: set `inbox_folder` in the brief (e.g., `dropbox:/assets/<campaign>`). The worker indexes files for reuse; no copies are made to an `ingested/` folder.
- Product image reuse: if no `product.image` provided, the worker selects the best matching image from the inbox by filename; falls back to GenAI if none.
- Outputs include:
  - Variants: `outputs/<campaign>/<product>/<ratio>/<market>.jpg`
  - Carousels: `outputs/<campaign>/carousels/<product>/slide_*.jpg`
  - Animated GIF: `outputs/<campaign>/videos/<product>/<market>.gif`
  - Localized messages: `outputs/<campaign>/messages/<product>_<market>.json`
  - Campaign catalog: `outputs/<campaign>/catalog.json`

Logging & Reporting
- Kafka topics: `pipeline.status.v1`, `assets.created.v1`, `compliance.v1`.
- CLI mode prints status; assets saved to storage backend.

Assumptions & Limitations
- Dropbox API and GenAI APIs may be unavailable in restricted environments; use local backend + stub generator.
- Logo detection is heuristic without explicit logo template matching.
