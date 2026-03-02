# Feature Specification: Background Task Processing

**Feature Branch**: `004-fastapi-background-tasks`
**Created**: 2026-03-03
**Status**: Draft
**Input**: User description: "Background tasks implementation using FastAPI background tasks feature"

## Clarifications

### Session 2026-03-03

- Q: Should async or sync be the default API behavior? → A: Async is the default. All endpoints return a tracking ID immediately. Sync mode available via `?sync=true` query parameter as a developer/testing escape hatch.
- Q: What happens to in-flight jobs if the server restarts? → A: Timeout-based expiry — jobs stuck in "processing" beyond a threshold (5 minutes) are auto-marked as "failed" when polled.
- Q: How long should completed job results be stored? → A: 1 hour TTL. Results are automatically cleaned up after 1 hour.
- Q: Can any client poll any job ID, or should there be access control? → A: No access control — the UUID itself is unguessable and serves as the access token.
- Q: Should the status endpoint include a polling hint? → A: Fixed `retry_after: 5` seconds in every "processing" response. Agent takes ~30s, so 5s intervals means ~6 polls instead of wasting requests.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Instant Chat Acknowledgment (Priority: P1)

A customer sends a support message via the web chat. Instead of waiting 30–40 seconds for the AI agent to finish its full tool-calling loop, they receive an immediate acknowledgment with a tracking identifier. The agent processes the request in the background. The customer can retrieve the final answer by checking the status of their request.

**Why this priority**: This is the core value — eliminating the 30–40 second blocking wait that makes the chat experience feel broken. Every channel (web, Gmail, WhatsApp) suffers from this today.

**Independent Test**: Send a POST to `/api/chat`, verify the response returns in under 2 seconds with a tracking identifier and a "processing" status. Then poll the status endpoint until the result is available.

**Acceptance Scenarios**:

1. **Given** a customer sends a chat message, **When** the request is received, **Then** the system returns a tracking identifier and "processing" status within 2 seconds.
2. **Given** a chat request is being processed in the background, **When** the agent completes, **Then** the result is stored and retrievable via the tracking identifier.
3. **Given** a chat request is being processed, **When** the customer polls before completion, **Then** the system returns "processing" status with no error.

---

### User Story 2 — Job Status and Result Retrieval (Priority: P1)

A customer (or frontend client) uses the tracking identifier from the acknowledgment to check whether the AI agent has finished processing. Once complete, they retrieve the full response. If the agent encountered an error, they see a user-friendly error message.

**Why this priority**: Without a way to retrieve results, the instant acknowledgment is useless. This is tightly coupled to US1 and equally critical.

**Independent Test**: Submit a chat request, receive a tracking ID, poll the status endpoint repeatedly, and verify the response transitions from "processing" to "completed" with the agent's answer included.

**Acceptance Scenarios**:

1. **Given** a job is still processing, **When** the client polls for status, **Then** the system returns `{"status": "processing"}`.
2. **Given** a job has completed successfully, **When** the client polls for status, **Then** the system returns `{"status": "completed", "response": "..."}`.
3. **Given** a job failed during processing, **When** the client polls for status, **Then** the system returns `{"status": "failed", "error": "..."}` with a user-friendly message.
4. **Given** a client provides an invalid or expired tracking ID, **When** they poll for status, **Then** the system returns a "not found" error.

---

### User Story 3 — Webhook Background Processing (Priority: P2)

External services (Gmail, WhatsApp) send webhook notifications to the system. The system must respond to the webhook within a few seconds to avoid timeout penalties and retries from the external provider. The AI agent processes the message in the background, and the result is stored for later retrieval or delivery.

**Why this priority**: Webhook providers (Gmail, WhatsApp) enforce strict timeout limits. If the endpoint takes 40 seconds to respond, the provider marks the webhook as failed and retries, causing duplicate processing. Background tasks solve this by returning 200 immediately.

**Independent Test**: Send a POST to `/api/webhooks/gmail`, verify HTTP 200 returns in under 2 seconds, then poll the job status endpoint to confirm the agent eventually processes the message.

**Acceptance Scenarios**:

1. **Given** Gmail sends a webhook notification, **When** the system receives it, **Then** it returns HTTP 200 with a tracking ID within 2 seconds and processes the message in the background.
2. **Given** WhatsApp sends a webhook notification, **When** the system receives it, **Then** it returns HTTP 200 with a tracking ID within 2 seconds and processes the message in the background.
3. **Given** a webhook message is processed in the background, **When** the agent completes, **Then** the result is stored and retrievable via the tracking ID.

---

### User Story 4 — Synchronous Developer Escape Hatch (Priority: P3)

Developers and testing tools (Swagger UI, curl scripts) sometimes need the old single request-response flow for debugging. The system supports an optional synchronous mode via `?sync=true` query parameter that waits for the full response, bypassing background processing.

**Why this priority**: Nice-to-have for developer experience and testing. The async flow is the default for all clients, but having a synchronous escape hatch simplifies debugging and manual testing in Swagger.

**Independent Test**: Send a POST to `/api/chat?sync=true`, verify the response contains the full agent answer (not just a tracking ID), matching the pre-feature behavior.

**Acceptance Scenarios**:

1. **Given** a developer sends a chat request with `?sync=true`, **When** the agent completes, **Then** the full response is returned in the same HTTP response.
2. **Given** a client sends a chat request without `?sync=true` (default), **When** the request is received, **Then** the system returns HTTP 202 with a tracking ID and processes in the background.

---

### Edge Cases

- What happens when the background task crashes mid-processing? Jobs stuck in "processing" for longer than 5 minutes are automatically considered "failed" when polled (timeout-based expiry). The status endpoint checks the job's creation timestamp and returns "failed" with a timeout error message.
- What happens when the job result storage is unavailable? The system should still accept requests and attempt processing — results may be lost but the system should not crash.
- What happens when a client polls for a job that was processed hours ago? Jobs should have a retention period after which they are cleaned up. Expired jobs return "not found".
- What happens when many concurrent requests are submitted? The system should accept all of them without blocking and process them in the order received.
- What happens if the same customer sends multiple messages rapidly? Each message gets its own tracking ID and is processed independently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST return an immediate acknowledgment with a unique tracking identifier for every chat and webhook request within 2 seconds.
- **FR-002**: System MUST process the AI agent workflow in the background after returning the acknowledgment.
- **FR-003**: System MUST provide a status endpoint where clients can check job status using the tracking identifier.
- **FR-004**: System MUST store the agent's final response and associate it with the tracking identifier upon completion.
- **FR-005**: System MUST mark jobs as "failed" with a user-friendly error message if the background task encounters an error.
- **FR-006**: System MUST support three job statuses: "processing", "completed", and "failed".
- **FR-007**: System MUST apply background processing to all three channels: web chat, Gmail webhook, and WhatsApp webhook.
- **FR-008**: System MUST default to async (background) processing for all chat and webhook endpoints. A `?sync=true` query parameter MUST be supported as a developer escape hatch that preserves the blocking behavior.
- **FR-009**: System MUST clean up completed and failed job results after 1 hour to prevent unbounded storage growth.
- **FR-010**: System MUST log the start, completion, and failure of every background job with the tracking identifier for observability.
- **FR-011**: System MUST preserve the existing correlation ID mechanism — the tracking identifier should be the correlation ID already generated per request.
- **FR-012**: System MUST handle concurrent background tasks without blocking each other.
- **FR-013**: System MUST return appropriate HTTP status codes: 202 Accepted for async responses, 200 OK for synchronous responses, 404 Not Found for unknown job IDs.
- **FR-014**: System MUST include a `retry_after: 5` field in every "processing" status response to guide client polling frequency.

### Key Entities

- **Job**: Represents a background processing request. Has a unique identifier (correlation ID), status (processing/completed/failed), the original request details, the agent's response (when complete), an error message (when failed), and timestamps for creation and completion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Chat and webhook endpoints return acknowledgment responses in under 2 seconds, compared to the current 30–40 seconds.
- **SC-002**: 100% of submitted requests are processed to completion or marked as failed — jobs stuck in "processing" beyond 5 minutes are automatically treated as "failed" when polled.
- **SC-003**: All existing functionality (customer lookup, KB search, ticket creation, response delivery) continues to work identically when triggered from a background task.
- **SC-004**: System can accept and queue 50+ concurrent chat requests without rejecting any, even while previous requests are still being processed.
- **SC-005**: Job results are retrievable for at least 1 hour after completion, giving clients sufficient time to poll for results.

## Assumptions

- The existing correlation ID system (`set_correlation_id()`) provides suitable unique identifiers for job tracking — no new ID generation mechanism needed.
- Job results will be stored in Redis (already available from feature 003) with TTL-based expiration for automatic cleanup, avoiding new database tables.
- FastAPI's built-in `BackgroundTasks` is sufficient for the current scale — no external task queue (Celery, Redis Streams) is needed at this stage.
- The frontend (not yet built) will implement polling logic; this feature only covers the backend API changes.
- Background task failures are captured and stored — no retry mechanism is included in this iteration.
