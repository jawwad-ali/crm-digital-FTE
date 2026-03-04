# API Contracts: Background Task Endpoints

**Feature**: 004-fastapi-background-tasks
**Date**: 2026-03-04

## Modified Endpoints

### POST /api/chat (async — default)

**Request**:
```
POST /api/chat
Content-Type: application/json

{
  "message": "How do I reset my password?",
  "email": "ali@test.com",
  "channel": "web",
  "name": "Ali"
}
```

**Response** (HTTP 202 Accepted):
```json
{
  "job_id": "a65c5987210846a08e4c57cc2cfa519e",
  "status": "processing",
  "retry_after": 5
}
```

### POST /api/chat?sync=true (synchronous — escape hatch)

**Request**: Same as above, with `?sync=true` query parameter.

**Response** (HTTP 200 OK):
```json
{
  "response": "To reset your password, go to Settings > Security...",
  "correlation_id": "a65c5987210846a08e4c57cc2cfa519e"
}
```

### POST /api/webhooks/gmail (async — default)

**Request**:
```
POST /api/webhooks/gmail
Content-Type: application/json

{
  "from_address": "customer@gmail.com",
  "body": "I need help with my order"
}
```

**Response** (HTTP 202 Accepted):
```json
{
  "job_id": "b72d1234567890abcdef1234567890ab",
  "status": "processing",
  "retry_after": 5
}
```

### POST /api/webhooks/whatsapp (async — default)

**Request**: Same structure as Gmail webhook.

**Response** (HTTP 202 Accepted): Same structure as Gmail webhook.

---

## New Endpoints

### GET /api/jobs/{job_id}

Poll for the status and result of a background job.

**Path parameters**:
- `job_id` (string, required): The tracking identifier returned from a chat or webhook request.

#### Response: Processing (HTTP 200)

```json
{
  "job_id": "a65c5987210846a08e4c57cc2cfa519e",
  "status": "processing",
  "response": null,
  "error": null,
  "retry_after": 5
}
```

#### Response: Completed (HTTP 200)

```json
{
  "job_id": "a65c5987210846a08e4c57cc2cfa519e",
  "status": "completed",
  "response": "To reset your password, go to Settings > Security...",
  "error": null,
  "retry_after": null
}
```

#### Response: Failed (HTTP 200)

```json
{
  "job_id": "a65c5987210846a08e4c57cc2cfa519e",
  "status": "failed",
  "response": null,
  "error": "An error occurred while processing your request. Please try again.",
  "retry_after": null
}
```

#### Response: Timed Out (HTTP 200)

When a job has been "processing" for more than 5 minutes:

```json
{
  "job_id": "a65c5987210846a08e4c57cc2cfa519e",
  "status": "failed",
  "response": null,
  "error": "Request timed out. Please try again.",
  "retry_after": null
}
```

#### Response: Not Found (HTTP 404)

When the job ID doesn't exist or has expired (past 1-hour TTL):

```json
{
  "error": "Job not found"
}
```

---

## Response Model Summary

| Endpoint | Default Status | Sync Mode Status | Model |
|----------|---------------|------------------|-------|
| POST /api/chat | 202 Accepted | 200 OK | JobAccepted / ChatResponse |
| POST /api/webhooks/gmail | 202 Accepted | N/A | JobAccepted |
| POST /api/webhooks/whatsapp | 202 Accepted | N/A | JobAccepted |
| GET /api/jobs/{job_id} | 200 OK / 404 | N/A | JobStatus |

---

## Error Responses

All endpoints preserve the existing global exception handler:

```json
{
  "error": "Internal server error",
  "detail": "..."
}
```

Status code: 500 Internal Server Error.
