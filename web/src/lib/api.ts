/**
 * API client for the Case Conference backend.
 * Supports both REST calls and Server-Sent Events streaming.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AgentConfig {
  role: string;
  model: string;
}

export interface LibrarianConfig {
  model: string;
  max_queries_per_turn: number;
}

export interface ConferenceRequest {
  query: string;
  agents: AgentConfig[];
  arbitrator_model: string;
  num_rounds: number;
  topology: string;
  enable_grounding: boolean;
  enable_fragility: boolean;
  fragility_tests: number;
  fragility_model: string;
  librarian?: LibrarianConfig;
}

export interface StreamEvent {
  event: string;
  data: Record<string, unknown>;
}

export interface AgentResponse {
  role: string;
  model: string;
  content: string;
  confidence: number;
  changed_from_previous: boolean;
}

export interface RoundResult {
  round_number: number;
  responses: AgentResponse[];
}

export interface ConferenceResult {
  conference_id: string;
  synthesis: {
    final_consensus: string;
    confidence: number;
    model: string;
  };
  dissent: {
    preserved: string[];
    rationale: string;
  };
  rounds: RoundResult[];
  grounding_report: Record<string, unknown> | null;
  fragility_report: Record<string, unknown> | null;
  total_tokens: number;
  total_cost: number;
  duration_ms: number;
}

export type StreamEventHandler = (event: StreamEvent) => void;

class APIClient {
  private apiKey: string = "";

  setApiKey(key: string) {
    this.apiKey = key;
  }

  getApiKey(): string {
    return this.apiKey;
  }

  private getHeaders(): HeadersInit {
    return {
      "Content-Type": "application/json",
      "X-API-Key": this.apiKey,
    };
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }

  async startConference(request: ConferenceRequest): Promise<{ conference_id: string; stream_url: string }> {
    const response = await fetch(`${API_BASE}/api/conference/start`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(error.detail || "Failed to start conference");
    }

    return response.json();
  }

  streamConference(
    conferenceId: string,
    onEvent: StreamEventHandler,
    onError: (error: Error) => void,
    onComplete: () => void
  ): () => void {
    const eventSource = new EventSource(`${API_BASE}/api/conference/${conferenceId}/stream`);

    // Track all event types we care about
    const eventTypes = [
      "conference_start",
      "librarian_start",
      "librarian_complete",
      "round_start",
      "agent_thinking",
      "agent_token",
      "agent_complete",
      "round_complete",
      "grounding_start",
      "grounding_complete",
      "arbitration_start",
      "arbitration_token",
      "arbitration_complete",
      "fragility_start",
      "fragility_test",
      "fragility_complete",
      "conference_complete",
      "error",
    ];

    eventTypes.forEach((eventType) => {
      eventSource.addEventListener(eventType, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          onEvent({ event: eventType, data });

          if (eventType === "conference_complete") {
            eventSource.close();
            onComplete();
          } else if (eventType === "error") {
            eventSource.close();
            onError(new Error(data.message || "Unknown error"));
          }
        } catch (err) {
          console.error("Failed to parse SSE event:", err);
        }
      });
    });

    eventSource.onerror = () => {
      eventSource.close();
      onError(new Error("Connection lost"));
    };

    // Return cleanup function
    return () => {
      eventSource.close();
    };
  }

  async analyzeDocuments(
    files: { filename: string; content_type: string; content_base64: string }[],
    query: string,
    model: string = "google/gemini-3-pro-preview"
  ): Promise<{
    session_id: string;
    summary: string;
    file_manifest: { filename: string; file_type: string; description: string }[];
    input_tokens: number;
    output_tokens: number;
  }> {
    const response = await fetch(`${API_BASE}/api/librarian/analyze`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ files, query, model }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(error.detail || "Failed to analyze documents");
    }

    return response.json();
  }

  async queryLibrarian(
    sessionId: string,
    question: string
  ): Promise<{
    question: string;
    answer: string;
    input_tokens: number;
    output_tokens: number;
  }> {
    const response = await fetch(`${API_BASE}/api/librarian/query`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ session_id: sessionId, question }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(error.detail || "Failed to query librarian");
    }

    return response.json();
  }
}

export const apiClient = new APIClient();

