Agent MCP Server
=================

This directory now includes a Model Context Protocol (MCP) server that exposes tools and resources for:

- Browsing generated outputs (campaigns, products, variants)
- Submitting human approvals (approve/reject) via Kafka
- Defining the exact information an LLM should see when drafting human‑readable alerts

Run
---

Prereqs: Python 3.13+, `uv` installed; Kafka reachable if you plan to publish approvals.

```bash
cd apps/agent-worker
uv run python mcp_server.py
```

Server Name: `creative-automation-mcp`

Environment
-----------

- `STORAGE_BACKEND` = `dropbox` (default) or `local`
- Dropbox (if `dropbox`): `DROPBOX_REFRESH_TOKEN`, `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, optional `DROPBOX_ROOT` (default `/Apps/CreativeAutomation`)
- Local (if `local`): `LOCAL_ROOT` (default `local_storage`)
- Kafka: `KAFKA_BROKER` (default `localhost:9092`)

Tools
-----

- `list_campaigns()` → `string[]`
- `list_products(campaign: string)` → `string[]`
- `get_variants(campaign: string, product: string)` → `{ ratio, path, target_market?, compliance_score? }[]`
- `approve(campaign: string, product: string, decision = "approved", reviewer?)` → publishes to `approvals.decision.v1`
- `get_alert_context(campaign: string)` → structured MCP payload for alerting
- `get_alert_prompt(campaign: string)` → deterministic text prompt with embedded MCP JSON

Resources
---------

- `alerts/instructions` → concise guidelines the LLM should use when drafting alerts.

Notes
-----

- The MCP alert context aggregates stats from `outputs/<campaign>` and any lineage JSON saved with variants.
- Approvals require Kafka; if Kafka is unavailable the tool raises an error.
- Paths in variant `path` values are returned with a `dropbox:` or `local:` scheme for downstream use.

