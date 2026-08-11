# Creative Automation Pipeline
 
 This project is a production-quality, **Creative Automation System** designed to accelerate marketing campaign workflows. It accepts a campaign brief, generates creative assets in multiple aspect ratios, and uses an AI agent to monitor for quality and diversity.
 
## 🚀 Key Features

- **Multi-Provider GenAI Integration**: Google Gemini 2.5 Flash Image, Adobe Firefly, OpenAI DALL-E 3 with intelligent fallback
- **Frontend**: Next.js 15 (App Router) with Tailwind CSS for a modern, responsive UI
- **Event-Driven**: Asynchronous processing using Kafka (Redpanda for local dev) for a scalable and resilient architecture
- **Comprehensive Compliance**: Brand guidelines, logo detection, legal content filtering, and automated reporting
- **Localization Engine**: Multi-language support with cultural adaptation for global markets
- **Agentic Monitoring**: A LangGraph-powered agent ensures creative outputs meet quality standards
- **Cloud Storage**: Dropbox is used as the source of truth for all assets, ensuring accessibility and organization
- **Local Development**: A `docker-compose.yml` and `Makefile` provide a simple, one-command setup

## 🏗️ Architecture

The system is composed of several microservices that communicate via Kafka. See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for detailed diagrams.

- **Frontend**: Uploads briefs and displays a real-time dashboard
- **Pipeline Worker**: Generates creative variants with compliance checking and localization
  - Ingests mixed assets (images, videos, audio, docs, graphics) from `inbox_folder` and reuses product images when available; otherwise uses Gemini Flash 2.5 for a single high-res image and resizes for aspect ratios. If `brand_name` is provided, prompts are tailored to the brand’s design language and may reference provided assets by filename for visual cues.
  - Saves generated and transient assets to Dropbox/local: variants, carousels, animated GIFs, localized messages, and a campaign catalog.
  - Optional logo overlay (brand-safe zone) applied before compliance when `logo_path` is provided.
- **Agent Worker**: Monitors and evaluates the generated assets using enhanced criteria
- **Realtime Gateway**: Pushes live status updates to the frontend via WebSockets

## 📋 Requirements

### Prerequisites

- [Node.js](https://nodejs.org/en) (v18+) and `pnpm`
- [Python](https://www.python.org/downloads/) (v3.11)
- [UV](https://docs.astral.sh/uv/) (fast Python package manager) - Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Docker](https://www.docker.com/products/docker-desktop/)

### API Keys Required

To use the enhanced GenAI features, you'll need API keys for at least one of the following providers:

- **Google Gemini 2.5 Flash Image**: [Get API Key](https://makersuite.google.com/app/apikey)
- **Adobe Firefly**: [Get Client ID & Secret](https://developer.adobe.com/firefly-api/)
- **OpenAI DALL-E 3**: [Get API Key](https://platform.openai.com/api-keys)

### Dropbox Configuration (App Key/Secret + Refresh Token)

To use Dropbox for asset storage, create a Dropbox app and complete OAuth 2.0 to obtain credentials:

1) Get your App Key and App Secret
- Create a Dropbox app in the App Console (https://www.dropbox.com/developers/apps) and sign in.
- Choose API: Dropbox API.
- Choose access type: App folder (recommended) or Full Dropbox (if you need full account access).
- Name the app and click Create app.
- On the app's Settings page, copy App key and App secret from the OAuth 2 section.

2) Get your Access Token and Refresh Token (long‑lived)
- Set a Redirect URI under Settings → OAuth 2. For testing you can use: https://www.dropbox.com/developers/
- In a browser, replace <YOUR_APP_KEY> and open:
  https://www.dropbox.com/oauth2/authorize?client_id=<YOUR_APP_KEY>&token_access_type=offline&response_type=code
- Authorize the app; you’ll be redirected with an authorization code in the URL.
- Exchange the code for tokens (replace placeholders):

```bash
curl https://api.dropboxapi.com/oauth2/token \
  -d code=<AUTHORIZATION_CODE> \
  -d grant_type=authorization_code \
  -u <YOUR_APP_KEY>:<YOUR_APP_SECRET>
```

- The JSON response contains a short‑lived access_token and a long‑lived refresh_token. Save both securely.

3) Use tokens in this project
- In `.env`, set the following (refresh flow preferred):

```bash
DROPBOX_APP_KEY=<YOUR_APP_KEY>
DROPBOX_APP_SECRET=<YOUR_APP_SECRET>
DROPBOX_REFRESH_TOKEN=<YOUR_REFRESH_TOKEN>
DROPBOX_ROOT=/Apps/CreativeAutomation

# Optional: if you also have a static long‑lived access token
# DROPBOX_ACCESS_TOKEN=<YOUR_ACCESS_TOKEN>
```

- The pipeline and frontend server routes use the refresh token to obtain short‑lived access tokens via the SDK. Keep all secrets secure.

## 🚀 Quick Start

### 1. Initial Setup

Clone the repository and configure your environment.

```bash
# Clone the repository
git clone <repository-url>
cd creative-automation-pipeline

# Copy the example environment file
cp .env.example .env
```

Now, open `.env` and add your **API credentials**:

```bash
# Required: Dropbox API credentials (refresh flow preferred)
DROPBOX_APP_KEY=your_dropbox_app_key
DROPBOX_APP_SECRET=your_dropbox_app_secret
DROPBOX_REFRESH_TOKEN=your_dropbox_refresh_token

# Optional: GenAI provider API keys (at least one recommended)
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
ADOBE_FIREFLY_CLIENT_ID=your_adobe_client_id_here
ADOBE_FIREFLY_CLIENT_SECRET=your_adobe_client_secret_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. Install Dependencies

This command will install `pnpm` packages for the frontend and set up Python environments with `UV` for the Python workers.

```bash
make setup
```

### 3. Start Services

This command starts Redpanda (Kafka) and the web UI for it using Docker Compose.

```bash
make run-services
# Or `docker compose up -d`
```

You can view the Redpanda console at [http://localhost:8080](http://localhost:8080).

### 4. Run Applications

Run each of the following commands in a **separate terminal window**:

```bash
# 1. Start the Next.js frontend
cd apps/frontend
pnpm dev
```

```bash
# 2. Start the realtime SSE gateway
cd apps/realtime-gateway
pnpm dev
```

```bash
# 3. Start the enhanced pipeline worker
cd apps/pipeline-worker
source .venv/bin/activate
uv run python main.py
```

```bash
# 4. Start the enhanced agent worker
cd apps/agent-worker
source .venv/bin/activate
uv run python agent_graph.py
```

```bash
# 4b. (Optional) Start the MCP server for alerts/approvals tools
cd apps/agent-worker
source .venv/bin/activate
uv run python mcp_server.py
```

Alternatively, to run a quick offline demo without Kafka/Dropbox:

```bash
cd apps/pipeline-worker
uv run python cli.py --brief ../../data/samples/brief_sample.json --storage-backend local --local-root ./local_storage
```

### 5. Run a Demo

Once all services are running, open a new terminal and run:

```bash
make demo
```

This will post the sample brief from `data/samples/brief_sample.json` to the API.

- Visit the **Upload Page** at [http://localhost:3000/upload](http://localhost:3000/upload)
- Check the **Dashboard** at [http://localhost:3000/dashboard](http://localhost:3000/dashboard) to see the live status updates and the final generated creatives
 - Use the **Approvals** UI at [http://localhost:3000/approvals](http://localhost:3000/approvals) or connect an MCP client to `creative-automation-mcp`

## 📖 Usage

### Campaign Brief Format

The system accepts campaign briefs in JSON format with the following structure:

```json
{
  "campaign_name": "Summer Refresh 2024",
  "brand_name": "Unnanu",
  "brand_palette": ["#e60023", "#6e56cf"],
  "target_market": "US West Coast",
  "target_audience": "Young adults, 18-30, interested in outdoor activities and sustainable products.",
  "campaign_message": "Stay cool, stay hydrated.",
  "products": [
    {
      "name": "Eco-Friendly Water Bottle",
      "image": null
    },
    {
      "name": "Lightweight Running Cap",
      "image": "dropbox:/assets/Summer Refresh 2024/cap_asset.jpg"
    }
  ],
  "logo_path": "dropbox:/assets/Summer Refresh 2024/logo.png",
  "inbox_folder": "dropbox:/assets/Summer Refresh 2024"
}
```

### Supported Target Markets

The system supports localization for the following markets:

- **US Markets**: US, US West Coast, US East Coast
- **Europe**: UK, Germany, France
- **Asia-Pacific**: Japan, India, Australia
- **Latin America**: Brazil

### Generated Assets

For each product, the system generates variants in three aspect ratios:

- **1:1** (1080x1080) - Square format for Instagram, Facebook
- **16:9** (1920x1080) - Landscape format for desktop ads, YouTube
- **9:16** (1080x1920) - Portrait format for mobile ads, Stories

## 🔧 Configuration

### Environment Variables

Key configuration options in your `.env` file:

```bash
# Frontend env loading in monorepo
# The frontend loads env variables from the repo root `.env` via next.config.ts.
# You can also create apps/frontend/.env.local if you prefer per-app overrides.

# Quality Thresholds
MIN_COMPLIANCE_SCORE=0.8      # Minimum compliance score (0.0-1.0)
MIN_LOCALIZATION_SCORE=0.7    # Minimum localization score (0.0-1.0)
MIN_QUALITY_SCORE=0.6         # Minimum quality score (0.0-1.0)
MAX_RETRY_ATTEMPTS=3          # Maximum retry attempts for failed generations

# Compliance Settings
BRAND_COMPLIANCE_ENABLED=true
LEGAL_CONTENT_FILTERING_ENABLED=true
LOGO_DETECTION_ENABLED=true

# Localization Settings
DEFAULT_TARGET_MARKET=US
SUPPORTED_LANGUAGES=en,de,fr,ja,pt
CULTURAL_ADAPTATION_ENABLED=true
```

### GenAI Provider Selection

The system automatically selects the best available GenAI provider:

1. **Google Gemini 2.5 Flash Image** (Priority: High) - Best for marketing images
2. **Adobe Firefly** (Priority: Medium) - Excellent for brand-safe content
3. **OpenAI DALL-E 3** (Priority: Low) - Reliable fallback option
4. **Stub Generator** (Priority: None) - Always available for testing

## 📊 Monitoring and Compliance

### Real-time Dashboard

The dashboard provides live updates on:

- Pipeline processing status
- Asset generation progress
- Compliance check results
- Quality metrics and scores
- Localization coverage
- Approvals stream (requested/decided), Performance metrics (Avg CTR/CPA), Privacy/Ethics flags

### Compliance Checks

Each generated asset undergoes comprehensive compliance verification:

- **Brand Compliance**: Logo presence, brand color usage, brand guidelines
- **Legal Content**: Prohibited words, content safety, legal requirements
- **Quality Assessment**: Image diversity, technical quality, aesthetic appeal

### Alerting System

The AI agent monitors for:

- Insufficient asset variants (< 3 per product)
- Low compliance scores (< 0.8)
- Poor image diversity
- Localization gaps
- Critical pipeline errors

## 🧪 Testing

### Running Tests

```bash
# Frontend tests
cd apps/frontend
pnpm test

# Pipeline worker tests
cd apps/pipeline-worker
source .venv/bin/activate
uv run pytest

# Agent worker tests
cd apps/agent-worker
source .venv/bin/activate
uv run pytest
```

### Sample Data

Use the provided sample brief to test the system:

```bash
make demo
```

This will submit a sample campaign brief and demonstrate the full pipeline workflow.

### Approvals

- When assets are created, an approval request is published to `approvals.request.v1` and a Slack message is sent if `SLACK_WEBHOOK_URL` is set. Use the dashboard or call:

```bash
curl "http://localhost:3000/api/approvals?campaign_name=Summer%20Refresh%202024&product=Eco-Friendly%20Water%20Bottle&decision=approved"
```

### Performance Metrics Ingestion

Publish mock ad performance metrics (CTR/CPA) to visualize in the dashboard:

```bash
python scripts/performance_ingest.py data/samples/performance.csv
```

## 🚀 Deployment

### Production Considerations

- **Kafka**: Use managed Kafka service (AWS MSK, Confluent Cloud)
- **Storage**: Dropbox Business or enterprise storage solution
- **Monitoring**: Prometheus + Grafana for metrics and alerting
- **Security**: API key rotation, network isolation, audit logging

### Docker Deployment

```bash
# Build and run with Docker Compose
docker compose -f docker-compose.prod.yml up -d

# Or use Kubernetes manifests
kubectl apply -f k8s/
```

## 📚 API Reference

### Endpoints

- `POST /api/briefs` - Submit a new campaign brief
- `GET /api/status` - Get pipeline status
- `GET /api/assets/{campaign}` - Get generated assets for a campaign

### Event Topics

- `briefs.ingest.v1` - New campaign brief received
- `pipeline.status.v1` - Pipeline processing updates
- `assets.created.v1` - New assets generated
- `compliance.v1` - Compliance check results
- `alerts.v1` - System alerts and notifications

## 🧠 Key Design Decisions

- Event-driven architecture: Kafka decouples components (frontend, pipeline worker, agent worker, gateway) for scalability and resilience.
- Storage source of truth: Dropbox stores briefs, raw inputs, and generated/finalized assets; local backend is available for offline/demo runs via a unified storage abstraction.
- Single high‑res generation: Generate one high‑quality base image per product, then crop/resize to 1:1, 16:9, 9:16 to reduce cost/latency and improve consistency.
- Provider selection: Prefer Gemini 2.5 Flash Image, then Firefly, OpenAI, with stub fallback; prompts enforce brand‑safe, center‑safe composition for crop‑robust outputs.
- Compliance engine: Weighted brand (logo/colors), legal, privacy (PII), and ethics checks; structured report emitted on `compliance.v1`.
- Localization: Rule‑based cultural adaptation for prompts; optional localized message JSON per product/market.
- Agentic monitoring: LangGraph agent tracks volume/diversity/compliance/localization; re‑publishes briefs with retry metadata and prompt guidance; alerts use MCP; approvals via Slack/web.
- Governance: Per‑variant lineage JSON, campaign catalog, retention policy, and finalized/ manifests per product for clean hand‑off and auditability.

## ⚠️ Assumptions & Limitations

- Alert LLM is stubbed locally: MCP and prompt are defined; swap in a production LLM (e.g., ChatOpenAI) in `agent-worker` when ready.
- Video is a lightweight animated GIF derived from images; true MP4 generation/transcoding is not included.
- Logo detection is heuristic; logo overlay assumes a provided logo (preferably with alpha). Automatic conflict resolution with image content is minimal.
- Security defaults: Kafka TLS/SASL and secret management are not enabled by default; recommended for production.
- Diversity check uses perceptual hash distance; it is not a full aesthetic or brand‑quality metric.
- Localization is rules‑based; no MT/translation provider is integrated; region‑specific legal disclaimers are not exhaustive.
- Performance metrics ingestion uses a mock CSV script; no direct ad network integrations (Meta/Google/TikTok) yet.
- Approvals persistence uses storage JSON files (no RDBMS); no RBAC/permissions model is included.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the [`docs/`](./docs/) directory
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Join the conversation in GitHub Discussions

## 🗺️ Roadmap

See [`docs/ROADMAP.md`](./docs/ROADMAP.md) for the complete development roadmap and upcoming features.

## 🔗 Related Links

- [Architecture Documentation](./docs/ARCHITECTURE.md)
- [Development Roadmap](./docs/ROADMAP.md)
- [Kafka Setup Guide](./KAFKA_SETUP.md)
- [Makefile Commands](./Makefile)

---

**Built with ❤️ for creative teams who need to scale their marketing campaigns efficiently.**
