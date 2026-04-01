## 2. System Architecture (Production Level)

### Current Prototype Status

The document below describes the target production architecture. The current repository implements a prototype subset:

- FastAPI backend with one realtime WebSocket endpoint
- Browser demo UI for mic capture and live translation display
- Chrome extension overlay for Google Meet, Microsoft Teams, and Zoho Meeting
- OpenAI-backed STT, translation, and TTS path
- Mock fallback mode when no real API key is present
- Direct text translation path for meeting-caption ingestion

What is not yet implemented at production level:

- fully managed microservice separation
- durable event bus or queue
- persistent session/transcript storage
- distributed scaling and orchestration
- production-grade conferencing integrations
- full observability stack

### Core Real-Time Flow

```text
Client speaks (English)
        |
        v
Audio Capture
        |
        v
Speech-to-Text (STT)
        |
        v
Translation Engine
        |
        v
Text-to-Speech (TTS)
        |
        v
Frontend UI (live captions + translated audio)
        |
        v
Team understands in real time
```

### Production Architecture Overview

```text
+-------------------+       WebSocket / WebRTC        +----------------------+
|   Speaker Client  |  -----------------------------> |   API Gateway        |
|  Mic + Web App    |                                 | Auth + Session Mgmt  |
+-------------------+                                 +----------+-----------+
                                                                   |
                                                                   v
                                                    +--------------+---------------+
                                                    |  Realtime Orchestrator       |
                                                    |  Stream routing + buffering  |
                                                    +---+--------------+-----------+
                                                        |              |
                         Partial transcripts            |              | translated events
                                                        |              |
                                                        v              v
                                         +--------------+---+     +---+-----------------+
                                         |  STT Service     |     | Translation Service |
                                         | streaming ASR    |     | EN -> HI / PA       |
                                         +--------+---------+     +----------+----------+
                                                  |                           |
                                                  | final text                | translated text
                                                  |                           |
                                                  v                           v
                                         +--------+---------------------------+--------+
                                         |         Caption/Event Bus                   |
                                         | pub/sub for transcript + translation events |
                                         +--------+---------------------------+--------+
                                                  |                           |
                                                  |                           |
                                                  v                           v
                                         +--------+---------+       +---------+--------+
                                         |   TTS Service    |       | Frontend Delivery |
                                         | streamed audio   |       | captions + status |
                                         +--------+---------+       +---------+--------+
                                                  |                           |
                                                  +-------------+-------------+
                                                                |
                                                                v
                                                    +-----------+-----------+
                                                    | Listener Client UI    |
                                                    | Hindi/Punjabi text    |
                                                    | + translated audio    |
                                                    +-----------------------+
```

### Recommended Service Breakdown

#### 1. Client Applications
- Speaker app captures microphone audio in small chunks, such as 100 to 300 ms frames.
- Listener app receives live captions, translated text, and synthesized audio.
- Frontend shows connection state, active language pair, partial transcript, final transcript, and playback controls.

#### 2. API Gateway
- Terminates secure client connections.
- Handles authentication, rate limiting, tenant isolation, and session creation.
- Routes each live session to the realtime orchestration layer.

#### 3. Realtime Orchestrator
- Maintains session state for each conversation room.
- Buffers, timestamps, and forwards audio chunks to the STT engine.
- Receives partial and final transcripts, sends them to translation, then dispatches caption and audio events to subscribed listeners.
- Coordinates retries, backpressure, and failover between providers where needed.

#### 4. Speech-to-Text Engine
- Uses streaming ASR for low-latency English transcription.
- Emits partial hypotheses quickly for live captions and final utterances for stable downstream translation.
- Adds confidence scores, timestamps, and speaker/session metadata.

#### 5. Translation Engine
- Translates English text to Hindi and Punjabi.
- Supports sentence-aware streaming so partial phrases can be shown fast while finalized text replaces them when stable.
- Can use glossary/domain terms for medical, warehouse, factory, or support environments.

#### 6. Text-to-Speech Engine
- Converts translated text to natural Hindi/Punjabi speech.
- Streams audio back in short segments so listeners hear near-real-time output.
- Supports voice selection, speed control, and caching for repeated phrases where useful.

#### 7. Caption/Event Bus
- Carries transcript, translation, status, and playback events between internal services and clients.
- Decouples STT, translation, TTS, and frontend delivery so each service can scale independently.
- Kafka, NATS, or Redis Streams are suitable depending on scale and durability needs.

#### 8. Data Layer
- Session store for active rooms, participants, and language preferences.
- Persistent storage for transcripts, translated text, audit logs, and analytics.
- Object storage for optional archived audio.

### End-to-End Request Lifecycle

1. The speaker's browser or mobile app captures microphone audio and sends compressed audio frames to the backend over WebSocket or WebRTC.
2. The API Gateway authenticates the request and assigns it to a realtime session.
3. The Realtime Orchestrator forwards audio frames to the streaming STT engine.
4. The STT engine emits partial English transcript updates for immediate live captions.
5. Once an utterance stabilizes, the transcript is sent to the Translation Engine.
6. The Translation Engine returns Hindi and/or Punjabi text.
7. The translated text is published to the listener UI for live caption display.
8. The same translated text is sent to the TTS service for synthesized speech.
9. The TTS service streams translated audio back to listeners with minimal delay.
10. All key events are logged for monitoring, analytics, transcript history, and quality review.

### Production Deployment Model

#### Frontend Layer
- Web app or mobile app for speakers and listeners.
- CDN for static assets.
- WebSocket/WebRTC edge connectivity for low-latency streaming.

#### Application Layer
- API Gateway instances behind a load balancer.
- Stateless Realtime Orchestrator pods or containers with horizontal scaling.
- Dedicated STT, Translation, and TTS microservices or managed AI provider adapters.

#### Messaging Layer
- Low-latency event streaming backbone for captions and audio job events.
- Dead-letter handling for failed TTS or translation jobs.

#### Storage Layer
- PostgreSQL or MySQL for users, sessions, settings, and transcript metadata.
- Redis for hot session state and low-latency caching.
- S3-compatible object storage for archived audio and transcript exports.

#### Observability Layer
- Centralized logs for each session trace.
- Metrics for latency, error rate, provider health, and active sessions.
- Distributed tracing across STT, translation, and TTS steps.

### Non-Functional Requirements

#### Latency Targets
- Audio capture to partial caption: under 1 second.
- Final transcript to translated caption: under 1 to 2 seconds.
- Final transcript to translated speech playback: under 2 to 3 seconds.

#### Scalability
- Services scale independently based on CPU, GPU, and concurrency profile.
- Session-aware routing prevents stream fragmentation.
- Event-driven design supports thousands of parallel sessions.

#### Reliability
- Automatic reconnection for clients.
- Fallback providers for STT, translation, or TTS failures.
- Idempotent event handling to avoid duplicate captions or audio.

#### Security
- TLS for all client and service traffic.
- Tenant-aware access control for enterprise deployments.
- Encryption at rest for transcripts and stored audio.
- Audit logging for sensitive environments.

### Suggested Technology Choices

#### Frontend
- React or Next.js for web clients
- WebSocket or WebRTC for realtime transport
- MediaRecorder or Web Audio API for microphone capture

#### Backend
- Node.js, Go, or Python for orchestration services
- FastAPI, NestJS, or Go Fiber for API and stream handling
- Redis for session cache and presence
- Kafka, NATS, or Redis Streams for event distribution

#### AI Layer
- Streaming STT provider
- Neural machine translation provider or LLM-based translation adapter
- Low-latency TTS provider with Hindi and Punjabi voice support

#### Infra
- Docker + Kubernetes for production deployment
- Nginx or cloud load balancer at the edge
- Prometheus + Grafana for metrics
- ELK or OpenSearch stack for logs

### Recommended Internal Modules

```text
/frontend
/api-gateway
/realtime-orchestrator
/services/stt-adapter
/services/translation-adapter
/services/tts-adapter
/services/caption-bus
/services/session-store
/services/analytics
```

### Architecture Summary

This system should be built as a low-latency, event-driven streaming platform. The client continuously sends audio, the backend transcribes it in real time, translates the text into Hindi or Punjabi, synthesizes translated speech, and pushes both captions and audio to listeners. For production use, the most important design priorities are low latency, service isolation, fault tolerance, and observability.
