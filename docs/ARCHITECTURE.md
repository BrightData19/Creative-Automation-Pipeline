# Creative Automation Pipeline: Architecture

This document outlines the technical architecture of the Creative Automation Pipeline. It is composed of a frontend for user interaction, an event bus for decoupling services, several backend workers for processing, and cloud storage for assets.

## 1. System Components

The system is designed as a set of loosely coupled microservices communicating via a central event bus (Kafka).

- **Frontend (Next.js)**: A web application for uploading campaign briefs and viewing generated creatives. It acts as the primary user interface.
- **Realtime Gateway (Node.js)**: A WebSocket/SSE server that consumes status and alert events from Kafka and broadcasts them to the frontend for a live dashboard experience.
- **Pipeline Worker (Python)**: The core processing engine. It consumes new briefs, fetches or generates assets, creates variants, and saves them to Dropbox.
- **Agent Worker (Python)**: An AI agent built with LangGraph that monitors the pipeline's output, ensures creative diversity and volume, and triggers alerts or remediation actions.
- **Event Bus (Kafka/Redpanda)**: The central nervous system. All services communicate asynchronously by producing and consuming events from Kafka topics.
- **Storage (Dropbox)**: The single source of truth for all files, including briefs, raw assets, and final outputs.

## 2. Data Flow & Diagrams

### 2.1. High-Level Pipeline Flow

The following diagram illustrates the end-to-end flow, from a user submitting a brief to the final assets being generated and monitored.

```mermaid
graph TD
    subgraph User Interaction
        A[Next.js Frontend] -->|1. POST /api/briefs| B(API Route)
        B -->|2. Upload brief.json| D(Dropbox)
        B -->|3. Publish briefs.ingest.v1| C(Kafka)
    end

    subgraph Backend Processing
        C -->|4. Consume| E(Pipeline Worker)
        E -->|5. Fetch assets| D
        E -->|6. Generate variants| E
        E -->|7. Save outputs| D
        E -->|8. Publish assets.created.v1| C
        E -->|8. Publish pipeline.status.v1| C
    end

    subgraph Agentic Monitoring
        C -->|9. Consume| F(Agent Worker)
        F -->|10. Evaluate outputs| F
        F -->|11. Publish alerts.v1| C
    end

    subgraph Realtime Dashboard
        C -->|12. Consume| G(Realtime Gateway)
        G -->|13. WebSocket push| A
    end

    style D fill:#22a,stroke:#fff,stroke-width:2px,color:#fff
    style C fill:#f90,stroke:#333,stroke-width:2px,color:#fff
```

### 2.2. Enhanced GenAI Integration Architecture

The system now supports multiple GenAI providers for image generation, with intelligent fallback and quality optimization.

```mermaid
graph TD
    subgraph GenAI Providers
        A[Gemini 2.5 Flash Image] --> C[Image Generation Engine]
        B[Adobe Firefly] --> C
        D[OpenAI DALL-E 3] --> C
        E[Stub Generator] --> C
    end

    subgraph Quality Control
        C --> F[Compliance Checker]
        F --> G[Brand Guidelines]
        F --> H[Legal Content Filter]
        F --> I[Logo Detection]
    end

    subgraph Output Processing
        I --> J[Variant Generator]
        J --> K[Localization Engine]
        K --> L[Final Assets]
    end

    style C fill:#4CAF50,stroke:#fff,stroke-width:2px,color:#fff
    style F fill:#FF9800,stroke:#fff,stroke-width:2px,color:#fff
```

### 2.3. Agent Worker (LangGraph) - Enhanced

The agent is a stateful graph that processes events and makes decisions. Each node represents a step in the agent's reasoning process.

```mermaid
graph TD
    Start((Start)) --> IngestEvent
    IngestEvent --> TrackOutputs
    TrackOutputs --> Evaluate{Evaluate Quality}
    Evaluate -->|Brand Compliance| BrandCheck
    Evaluate -->|Legal Content| LegalCheck
    Evaluate -->|Diversity & Count| DiversityCheck

    BrandCheck --> ComplianceResult{Compliance OK?}
    LegalCheck --> LegalResult{Legal OK?}
    DiversityCheck --> DiversityResult{Diversity OK?}

    ComplianceResult -->|No| ComposeAlert
    LegalResult -->|No| ComposeAlert
    DiversityResult -->|No| RetryOrFinalize

    ComplianceResult -->|Yes| Finalize
    LegalResult -->|Yes| Finalize
    DiversityResult -->|Yes| Finalize

    RetryOrFinalize -->|Retry| RegenerateRequest
    RegenerateRequest --> IngestEvent
    RetryOrFinalize -->|Max Retries| ComposeAlert

    ComposeAlert --> EmitAlert
    EmitAlert --> Finalize((End))
```

### 2.4. Compliance and Quality Assurance Flow

```mermaid
graph TD
    subgraph Input Validation
        A[Campaign Brief] --> B[Content Analysis]
        B --> C[Brand Guidelines Check]
        B --> D[Legal Content Filter]
    end

    subgraph Asset Generation
        E[GenAI Generation] --> F[Logo Detection]
        F --> G[Brand Color Validation]
        G --> H[Quality Assessment]
    end

    subgraph Output Validation
        H --> I[Compliance Report]
        I --> J[Approval Workflow]
        J --> K[Final Assets]
    end

    style C fill:#2196F3,stroke:#fff,stroke-width:2px,color:#fff
    style D fill:#F44336,stroke:#fff,stroke-width:2px,color:#fff
    style F fill:#4CAF50,stroke:#fff,stroke-width:2px,color:#fff
```

## 3. Kafka Topics

- `briefs.ingest.v1`: Signals a new campaign is ready for processing.
- `pipeline.status.v1`: Provides real-time updates on the generation process.
- `assets.created.v1`: Announces the successful creation of a set of creative variants.
- `alerts.v1`: Carries human-readable alerts from the agent for system monitoring.
- `compliance.v1`: Reports on brand compliance and legal content checks.

## 4. Technology Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Backend Workers**: Python 3.11, LangChain, LangGraph, Pydantic
- **Realtime Gateway**: Node.js, Kafkajs, ws
- **Event Bus**: Redpanda (local), Kafka (prod)
- **Storage**: Dropbox API
- **GenAI Providers**: Google Gemini 2.5 Flash Image, Adobe Firefly, OpenAI DALL-E 3
- **Image Processing**: Pillow (PIL), OpenCV
- **Compliance**: Custom brand guidelines engine, legal content filtering
- **Containerization**: Docker Compose

## 5. Security and Compliance

- **API Key Management**: Secure storage of GenAI provider API keys
- **Content Filtering**: Automated detection of prohibited content
- **Brand Protection**: Logo detection and brand guideline enforcement
- **Audit Trail**: Complete logging of all generation requests and compliance checks
- **Data Privacy**: Secure handling of campaign briefs and generated assets

## 6. Scalability Considerations

- **Horizontal Scaling**: Worker services can be scaled independently
- **Load Balancing**: Kafka partitions enable parallel processing
- **Caching**: Redis integration for frequently accessed assets and prompts
- **CDN**: CloudFront integration for global asset delivery
- **Monitoring**: Prometheus metrics and Grafana dashboards
