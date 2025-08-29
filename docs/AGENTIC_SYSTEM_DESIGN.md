# Agentic System Design

This document describes the AI-driven agent that monitors the creative pipeline, triggers automated actions, and communicates issues to stakeholders.

## Overview

- Monitors Kafka topics: `briefs.ingest.v1`, `pipeline.status.v1`, `assets.created.v1`, `compliance.v1`.
- Tracks per-campaign state: products, variants, diversity hashes, compliance scores, localization coverage, and processing stages.
- Evaluates quality along three pillars: diversity/volume, brand/legal compliance, and localization coverage.
- Triggers automated retries by re-publishing the original brief when quality thresholds are not met.
- Emits human-readable alerts via `alerts.v1` using a Model Context Protocol (MCP).

## Graph Nodes (LangGraph)

- `track_outputs`: Downloads variants (from Dropbox/local), computes perceptual hash, and updates product state.
- `evaluate_quality`: Ensures at least 3 variants per product and checks visual diversity via Hamming distance.
- `evaluate_compliance`: Aggregates compliance reports per product and rolls up an overall score.
- `evaluate_localization`: Computes localization coverage and per-product localization scores.
- `retry_or_finalize_enhanced`: Decides whether to re-trigger generation (and publishes a new `briefs.ingest.v1` event) or finalize.
- `compose_alert` → `draft_message` → `emit_alert`: Builds MCP, drafts a human-readable message, and emits the alert to Kafka.

## Automated Triggering

Criteria to trigger re-generation (any of the below):

- Overall performance score < 0.75
- Compliance score < 0.8
- Localization score < 0.7
- Quality/diversity score < 0.6
- Critical issues detected (e.g., pipeline errors)

On trigger, the agent re-publishes the last `briefs.ingest.v1` event with a new `event_id` and `retry_attempt` incremented. This keeps the pipeline decoupled and idempotent.

## Model Context Protocol (MCP)

The MCP provides a structured payload to any LLM used for drafting stakeholder-friendly alerts. See `docs/MCP.md` for schema and formatting.

## Alerting and Audience Routing

- Issue types map to audiences: marketing, creative, IT, legal.
- Alerts include: campaign, issue type, impact, recommended next steps, and audience.

## Observability

- Metrics: total assets, diversity score, compliance score, localization score, issue counts, campaign status.
- Logs: retry reasons, attempt counters, per-stage processing milestones.

## Extensibility

- Add remediation actions: prompt adjustments, provider switching, or targeted product-only regeneration topics.
- Integrate Slack/Email/PagerDuty sinks consuming `alerts.v1`.

