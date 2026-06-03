Purplle-Vision-AI Store Intelligence
Architecture Decisions Report

This document explains the key engineering decisions behind the system, focusing on why specific design paths were chosen over alternative approaches.

The guiding principle throughout development was:

Build a system that reliably converts raw CCTV signals into actionable retail intelligence with minimal infrastructure overhead and maximum behavioral accuracy.

1. Vision Pipeline Strategy: Classical CV over Foundation Models
 Problem

We needed a system that can:

Detect people in real-time CCTV feeds
Maintain consistent identity over time
Support zone-level behavioral tracking
Work reliably on edge hardware

Approaches Evaluated
Large Vision-Language Models (frame-based reasoning)
Transformer-based detectors (RT-DETR style)
Classical detection + tracking pipeline

Alternative Idea (AI Recommendation)

A model-driven approach was suggested:

Sample frames periodically
Send them to multimodal AI
Ask the model to return bounding boxes and tracking info

While attractive for simplicity, it depends heavily on external inference APIs and lacks temporal consistency.

Final Decision: YOLOv8 + ByteTrack
Why this approach was chosen:

1. Identity continuity matters more than detection alone
Retail analytics depends on tracking the same person across time. ByteTrack provides stable ID propagation even under partial occlusion.

2. Predictable performance in real environments
CCTV feeds are noisy: motion blur, crowding, lighting variation. YOLOv8 remains stable under these conditions without external dependencies.

3. Works fully at the edge
No network calls, no API latency, no cost per frame — making it suitable for deployment in real store environments.

4. Handles real-world occlusion better than frame-only reasoning models
Customers frequently overlap in queues and aisles; ByteTrack preserves identity through short detection gaps.

✔ Outcome

A deterministic, low-latency pipeline that prioritizes tracking consistency over semantic reasoning per frame.

2. Data Representation Design: Event Stream over Session Storage

Problem

We needed a way to represent store activity that supports:

Continuous ingestion from video streams
Multi-camera environments
Reliable analytics reconstruction
Fault tolerance under interruptions
 Design Alternatives
In-memory session tracking per visitor
Event-based immutable logging system
 Alternative Idea (AI Recommendation)

A session-centric model was suggested:

Maintain live state per visitor
Update their journey continuously in memory
Emit a final aggregated record when they exit

This simplifies query logic but tightly couples system reliability to runtime memory.

Final Decision: Immutable Event Stream

Instead of storing sessions, the system emits atomic events such as:

Entry into store
Zone transitions
Dwell updates
Queue interactions

Each event is independent and stored permanently.

Why this design was chosen:

1. Resilience to system failure
If the pipeline stops unexpectedly, already emitted events remain intact.

2. Easy duplication handling
Every event carries a unique identifier, allowing safe retries without corruption.

3. Flexible analytics layer
Sessions, funnels, and dwell metrics are reconstructed later using SQL queries rather than precomputed state.

4. Better observability
Raw event logs preserve full transparency of customer movement.

 Outcome

A robust, replayable data model that prioritizes durability and analytical flexibility over in-memory convenience.

3. Storage & Query Layer: Embedded Database over Distributed Systems
 Problem

The system requires:

Real-time ingestion of events
Fast analytical queries (funnels, heatmaps, dwell analysis)
Minimal deployment complexity
Single-command execution for evaluation
Options Evaluated
Full distributed stack (PostgreSQL + Redis + worker queues)
External OLAP warehouse systems
Embedded database approach
Alternative Idea (AI Recommendation)

A microservices-style architecture was initially proposed:

PostgreSQL for persistence
Redis for buffering
Background workers for analytics aggregation

While scalable, it introduces significant operational overhead.

 Final Decision: SQLite (WAL mode) + Direct Query Layer
Why this approach was selected:

1. Minimal deployment friction
The entire system runs locally without needing database servers or orchestration tools.

2. Sufficient performance for single-store analytics
The workload is append-heavy with read-based analytics, which SQLite handles efficiently in WAL mode.

3. Tight integration with API layer
FastAPI interacts directly with the database, reducing system complexity and latency.

4. Portable execution model
The system can be moved across machines as a single container or file-based deployment.

 Outcome

A lightweight, self-contained architecture that trades distributed complexity for operational simplicity and fast evaluation readiness.

 Overall Engineering Philosophy

Across all decisions, the system follows a consistent philosophy:

• Prefer reliability over theoretical scalability

The system is optimized for real store environments, not large distributed clusters.

• Prefer traceability over abstraction

Every event is stored in its raw form for full auditability.

• Prefer deterministic pipelines over probabilistic shortcuts

Stable tracking is prioritized over AI-generated inference per frame.

• Prefer deployability over infrastructure richness

The system is designed to run with minimal setup and zero external dependencies.
Summary

Purplle-Vision-AI store Intelligence is structured around a simple idea:

Convert noisy CCTV data into a clean, replayable event stream that can be analyzed reliably and deployed easily.

The architecture intentionally avoids unnecessary complexity while maintaining production-grade analytical capability.
