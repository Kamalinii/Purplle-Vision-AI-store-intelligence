Purplle Vision AI  Store Intelligence API — Architecture Design

## Overview

Purplle Vision AI is an end-to-end retail analytics system that converts raw CCTV footage into actionable business intelligence for physical stores.

The system consists of four major layers:

1. Detection Layer
2. Event Processing Layer
3. Intelligence API Layer
4. Live Dashboard Layer

The objective is to accurately measure the store conversion funnel:

Visitor → Zone Visit → Billing Queue → Purchase

while handling real-world challenges such as staff movement, re-entry, multiple cameras, and incomplete detections.

---

# System Architecture

## 1. Detection Layer

The detection layer processes CCTV footage from multiple cameras.

Responsibilities:

* Detect people in video frames
* Track identities across frames
* Assign visitor IDs
* Detect zone transitions
* Generate business events

The detector continuously analyzes frames and emits structured events whenever a customer enters, exits, changes zones, waits in billing, or re-enters the store.

Generated events follow the challenge schema and become the single source of truth for downstream analytics.

---

## 2. Event Processing Layer

The event ingestion service receives event batches through:

POST /events/ingest

Responsibilities:

* Schema validation
* Deduplication
* Database persistence
* Partial failure handling
* Idempotent processing

I intentionally chose an event-driven architecture because it cleanly separates computer vision logic from business analytics.

The API does not need to understand how detections were generated. It only consumes standardized events.

This separation makes the system easier to scale and maintain.

---

## 3. Intelligence Layer

The intelligence layer computes business metrics from stored events.

Implemented analytics include:

### Metrics

* Unique visitors
* Conversion rate
* Queue depth
* Abandonment rate
* Average dwell per zone

### Funnel

Entry → Zone Visit → Billing Queue → Purchase

### Heatmap

Zone-level analytics:

* Visit frequency
* Average dwell
* Normalized scores (0–100)

### Anomaly Detection

Current anomaly detection monitors:

* Queue congestion
* High abandonment
* Low conversion
* Traffic surges

The analytics layer intentionally computes results dynamically rather than storing precomputed aggregates.

This ensures dashboard metrics always reflect the latest event stream.

---

## 4. Dashboard Layer

The dashboard provides a real-time operational view.

Features:

* Live CCTV streams
* KPI monitoring
* Conversion funnel visualization
* Heatmap rendering
* Store health monitoring

The dashboard periodically polls API endpoints instead of maintaining WebSocket connections.

For the scale of this challenge, polling reduced complexity while still providing near real-time updates.

---

# Database Design

SQLite was selected as the primary datastore.

Reasons:

* Zero external dependencies
* Easy local execution
* Sufficient for challenge-scale workloads
* Simple deployment

The database stores:

* Event records
* POS transactions
* Session information

Indexes are used on frequently queried fields such as:

* store_id
* visitor_id
* timestamp

to improve analytics performance.

---

# Reliability Considerations

Several production-style behaviors were implemented:

### Structured Logging

Every request generates:

* trace_id
* endpoint
* latency
* status code
* store identifier

This makes debugging significantly easier.

### Graceful Degradation

Database failures return structured HTTP 503 responses instead of raw exceptions.

### Health Monitoring

The /health endpoint provides a centralized service status check.

---

# AI-Assisted Decisions

AI tools were used extensively during development.

## Decision 1: Event-Driven Architecture

An LLM suggested directly calculating metrics from the detection pipeline.

I rejected this approach.

Instead, I introduced an event ingestion layer because it separates detection from analytics and mirrors real production systems.

This also makes testing significantly easier.

---

## Decision 2: Re-Identification Strategy

Several approaches were explored:

* Deep ReID embeddings
* Color histogram matching
* Appearance-based matching

For this challenge I selected histogram-based matching because it provided an acceptable balance between implementation complexity and runtime cost.

Although deep embeddings would likely improve accuracy, they would introduce additional dependencies and computational overhead.

---

## Decision 3: Dashboard Design

AI suggested implementing WebSockets.

I chose periodic polling instead.

The challenge requires live updates, but not massive scale.

Polling every few seconds provides simpler implementation while maintaining responsiveness.

This reduced engineering complexity and made debugging easier during development.

---


> [!IMPORTANT]
> This document provides a high-level architectural overview of the Apex Retail Store . Every decision in this architecture was made to support the **North Star Metric: Offline Store Conversion Rate**, ensuring that raw pixels are accurately transformed into actionable business intelligence.

---

## 1. Architecture Overview

The system is designed with a strict decoupling between the heavy computer vision workload (Detection Pipeline) and the lightweight, high-concurrency analytical engine (Intelligence API). This guarantees that camera stream latency never blocks dashboard analytics, and vice-versa.


mermaid
graph TD
    subgraph Edge Detection Node
        C1["Camera 1: Entry"] -->|"Video Stream"| Y["YOLOv8 + ByteTrack"]
        C2["Camera 2: Skincare"] -->|"Video Stream"| Y
        C3["Camera 3: POS"] -->|"Video Stream"| Y
    end

    subgraph Intelligence API Engine
        Y -->|"POST /events/ingest"| API["FastAPI Ingestion Endpoint"]
        API -->|"Async Upsert"| DB[("SQLite WAL")]
        DB -->|"Real-time Query"| M1["/metrics"]
        DB -->|"Real-time Query"| M2["/funnel"]
        DB -->|"Real-time Query"| M3["/heatmap"]
    end

    subgraph Client Application
        M1 --> UI["Live Dashboard SPA"]
        M2 --> UI
        M3 --> UI
    end


###  1.1 The Detection Pipeline (Vision Layer)
The vision layer operates as a headless, concurrent consumer of CCTV video streams.
- **Model Choice:** We use **YOLOv8** for real-time bounding box detection, optimized for partial occlusions common in retail environments.
- **Temporal Tracking:** Raw detections are meaningless without temporal persistence. We employ **ByteTrack** for Re-ID (Re-Identification), which uses Intersection-over-Union (IoU) heuristics to maintain a stable visitor_id even when customers cross paths.
- **Event Emission:** The pipeline continuously evaluates spatial coordinates against predefined zone polygons (from store_layout.json). When thresholds are crossed, it emits stateless, point-in-time events (e.g., ZONE_ENTER, ZONE_DWELL).

### 1.2 The Intelligence API (Data Layer)
The data layer is built on **FastAPI** to handle high-velocity asynchronous I/O.
- **Idempotent Ingestion:** The /events/ingest endpoint accepts batches of events. It relies on the database's native constraints (INSERT OR IGNORE) utilizing the event_id to ensure idempotency. If the network drops and the vision node retries a batch, the system remains perfectly consistent.
- **Embedded Storage:** We utilize **SQLite** with Write-Ahead Logging (PRAGMA journal_mode=WAL). For edge deployments in physical retail stores, embedded databases eliminate the operational overhead of managing external database clusters while easily handling the throughput of a single store.
- **Sessionization on Read:** Rather than attempting to maintain complex state machines during ingestion, the API stores raw ledger events. Session correlation (e.g., deduplicating a customer who stepped outside and immediately re-entered) is calculated on-the-fly when the dashboard queries the /funnel endpoint.

---

## 🤖 2. AI-Assisted Decisions

This project leveraged Large Language Models (LLMs) and Vision-Language Models (VLMs) as active engineering co-pilots. Below are three specific instances where AI significantly shaped the system's design.

### 📍 Decision 1: Spatial Mapping for the Heatmap UI
- **The Problem:** The store_layout.json contained semantic zone names, but the dashboard required exact CSS pixel coordinates to render the live heatmap over the floorplan image.
- **AI Suggestion:** Initially, I attempted to manually map generic percentage coordinates. When this failed to align with the visual feed, the AI suggested utilizing the native Apple Vision API to perform Optical Character Recognition (OCR) directly on the layout.png file to extract the exact bounding boxes of text labels (like "Makeup Unit").

> [!NOTE]
> **Outcome:** *Agreed and Implemented.* This bridging of raw image processing and UI logic was extremely successful. The AI generated a script to extract the exact (x,y) layout coordinates, allowing the frontend heatmap dots to pulse with pixel-perfect accuracy over the floorplan.

### Decision 2: Stateful vs. Stateless Ingestion
- **The Problem:** Designing the DetectionEvent schema payload to send from the cameras to the API.
- **AI Suggestion:** The AI strongly advocated for a complex, stateful ORM design using SQLAlchemy. It proposed creating a "Session" object in the database, and updating that same row every time a customer moved to a new zone.

> [!WARNING]
> **Outcome:** *Overrode.* I explicitly rejected the stateful design. In distributed systems (like 5 cameras operating concurrently), stateful updates lead to severe race conditions and database locks. I instructed the AI to pivot to an append-only "Event Ledger" schema. Events are dumped instantly, and state is derived via SQL GROUP BY logic later. This decision massively increased ingestion throughput and resilience.

### Decision 3: Idempotency Enforcement Mechanism
- **The Problem:** Ensuring POST /events/ingest is completely idempotent as per the challenge constraints.
- **AI Suggestion:** The AI recommended standing up a Redis container to act as a caching layer. The API would check if event_id in redis before inserting into the database.
# Future Improvements

If extended beyond the challenge, I would prioritize:

* Deep ReID embeddings
* Cross-camera identity tracking
* WebSocket-based dashboard updates
* Historical trend analytics
* Predictive queue forecasting
* Multi-store aggregation


