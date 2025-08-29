# Data Privacy, Ethics, Security, and Governance

This document summarizes the controls and implementation added to the Creative Automation Pipeline.

## Data Privacy

- PII Detection and Masking: `apps/pipeline-worker/privacy.py`
  - Detects emails, phone numbers, SSN, and credit card-like sequences in text.
  - Masks PII in pipeline status `detail` by default (`REDACT_PII=true`).
- Compliance Integration: Privacy results included in the compliance report under `privacy_compliance`.
- Storage: Transient and generated assets are organized by campaign for clear discovery and removal.

## Ethics

- Ethical Language Checks: `EthicsChecker` in `apps/pipeline-worker/compliance.py` flags biased terms and references to protected classes for careful handling.
- Included in `compliance_breakdown.ethics_compliance` and contributes to the overall score.

## Security (Data)

- Transport: Dropbox API usage is over TLS; Kafka can be configured for TLS in production (not included in local compose).
- At-rest: Optional retention policy cleanup prevents indefinite storage (`RETENTION_DAYS`).
- Event Redaction: Status details are redacted for PII before emission to Kafka.

## Governance (Data)

- Lineage & Metadata: Per-variant JSON metadata saved alongside each output JPG with fields: campaign, product, ratio, market, source (provided | reused_inbox | genai), generator provider, prompt hash, compliance score, timestamp.
- Campaign Catalog: `outputs/<campaign>/catalog.json` includes `created_at` and basic product list.
- Retention: `apps/pipeline-worker/governance.py` can delete campaigns older than `RETENTION_DAYS` from storage (Dropbox/local) when configured.

## Data Visualization

- Dashboard Observability: `apps/frontend/src/app/dashboard/page.tsx`
  - Topic filters (Briefs, Pipeline, Assets, Compliance, Alerts, Other)
  - Metrics: Avg Compliance, PII Flags, Ethics Flags, plus per-topic counts
  - Live event feed with compliance summaries

## Recommended Production Hardening

- Secrets Management: Use a secret manager for API keys, not `.env`.
- TLS for Kafka: Enable brokers and clients with TLS + SASL.
- S3/Dropbox Object Encryption: Enable provider-managed encryption; consider client-side encryption for highly sensitive content.
- DLP/PII: Expand detection with ML/NLP or dedicated DLP services; add image OCR PII.
- Audit Logging: Ship structured logs to a SIEM; include redaction flags.
- Access Controls: Introduce roles and policies for who can retrieve/download assets.

