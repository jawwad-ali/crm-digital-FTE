// Client-side message in conversation thread
export interface Message {
  id: string;
  role: "customer" | "agent";
  content: string;
  timestamp: Date;
  status: "sent" | "processing" | "completed" | "failed";
  jobId?: string;
  error?: string;
}

// Ordered collection of messages for the current session
export interface Conversation {
  messages: Message[];
  customerName: string;
  customerEmail: string;
  isFollowUpMode: boolean;
}

// POST /api/chat request body
export interface ChatRequest {
  name: string;
  email: string;
  message: string;
  channel: "web";
}

// POST /api/chat response (HTTP 202)
export interface JobAccepted {
  job_id: string;
  status: "processing";
  retry_after: number;
}

// POST /api/chat?sync=true response (HTTP 200)
export interface ChatResponse {
  response: string;
  correlation_id: string;
}

// GET /api/jobs/{job_id} response
export interface JobStatus {
  job_id: string;
  status: "processing" | "completed" | "failed";
  response: string | null;
  error: string | null;
  retry_after: number | null;
}

// GET /health response
export interface HealthStatus {
  status: string;
}

// Client-side form validation errors
export interface ValidationErrors {
  name?: string;
  email?: string;
  message?: string;
}
