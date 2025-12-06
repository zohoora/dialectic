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

// Patient context for intelligent routing
export interface PatientContext {
  age?: number;
  sex?: "male" | "female" | "other";
  comorbidities?: string[];
  current_medications?: string[];
  allergies?: string[];
  failed_treatments?: string[];
  relevant_history?: string;
  constraints?: string[];
}

// Model configuration for system components
export interface V3ModelConfig {
  router_model: string;      // Model for intelligent routing
  classifier_model: string;  // Model for query classification (fast/cheap)
  surgeon_model: string;     // Model for heuristic extraction
  scout_model: string;       // Model for Scout analysis
  validator_model: string;   // Model for speculation validation
}

export interface ConferenceRequest {
  query: string;
  agents: AgentConfig[];
  arbitrator_model: string;
  enable_grounding: boolean;
  enable_fragility: boolean;
  fragility_tests: number;
  fragility_model: string;
  librarian?: LibrarianConfig;
  // Patient context for routing
  patient_context?: PatientContext;
  // Conference options
  enable_scout?: boolean;
  enable_routing?: boolean;
  enable_learning?: boolean;
  // Overrides (router decides by default)
  mode_override?: string;
  topology_override?: string;
  // Model configuration
  model_config_v3?: V3ModelConfig;
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
    key_points?: string[];
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

// =============================================================================
// CONFERENCE TYPES
// =============================================================================

export type ConferenceMode = 
  | "STANDARD_CARE" 
  | "COMPLEX_DILEMMA" 
  | "NOVEL_RESEARCH" 
  | "DIAGNOSTIC_PUZZLE";

// v3: Topology types
export type ConferenceTopology =
  | "free_discussion"
  | "oxford_debate"
  | "delphi_method"
  | "socratic_spiral"
  | "red_team_blue_team";

export interface ScoutCitation {
  title: string;
  authors: string[];
  journal?: string;
  year: number;
  pmid?: string;
  evidence_grade: string;
  key_finding: string;
}

export interface ScoutReport {
  is_empty: boolean;
  query_keywords: string[];
  total_found: number;
  meta_analyses: ScoutCitation[];
  high_quality_rcts: ScoutCitation[];
  preliminary_evidence: ScoutCitation[];
  conflicting_evidence: ScoutCitation[];
}

export interface RoutingDecision {
  mode: ConferenceMode;
  active_agents: string[];
  activate_scout: boolean;
  rationale: string;
  complexity_signals: string[];
  topology: ConferenceTopology;
  topology_rationale: string;
  topology_signals: string[];
}

export interface ClinicalConsensus {
  recommendation: string;
  evidence_basis: string[];
  confidence: number;
  safety_profile: string;
  contraindications: string[];
}

export interface ExploratoryConsideration {
  hypothesis: string;
  mechanism: string;
  evidence_level: string;
  potential_benefit: string;
  risks: string[];
  what_would_validate: string;
}

export interface Tension {
  description: string;
  lane_a_position: string;
  lane_b_position: string;
  resolution: string;
}

export interface V2Synthesis {
  clinical_consensus: ClinicalConsensus;
  exploratory_considerations: ExploratoryConsideration[];
  tensions: Tension[];
  safety_concerns: string[];
  stagnation_concerns: string[];
  what_would_change: string;
  preserved_dissent: string[];
  overall_confidence: number;
}

export interface LaneResult {
  lane: "A" | "B";
  responses: AgentResponse[];
}

export interface FragilityResult {
  perturbation: string;
  outcome: "survives" | "modifies" | "collapses";
  explanation: string;
  modified_recommendation?: string;
}

export interface FragilityReport {
  perturbations_tested: number;
  survival_rate: number;
  is_fragile: boolean;
  results: FragilityResult[];
}

export interface V2ConferenceResult {
  conference_id: string;
  query: string;
  mode: ConferenceMode;
  routing: RoutingDecision;
  scout_report?: ScoutReport;
  lane_a?: LaneResult;
  lane_b?: LaneResult;
  synthesis: V2Synthesis;
  fragility_report?: FragilityReport;
  total_tokens: number;
  total_cost: number;
  duration_ms: number;
}

export type StreamEventHandler = (event: StreamEvent) => void;

class APIClient {
  private getHeaders(): HeadersInit {
    // API key is managed by the backend via environment variables
    return {
      "Content-Type": "application/json",
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

    // All supported event types
    const eventTypes = [
      // Core events
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
      // Lane-based events
      "routing_start",
      "routing_complete",
      "scout_start",
      "scout_complete",
      "lane_a_start",
      "lane_a_agent",
      "lane_a_complete",
      "lane_b_start",
      "lane_b_agent",
      "lane_b_complete",
      "cross_exam_start",
      "cross_exam_critique",
      "cross_exam_complete",
      "feasibility_start",
      "feasibility_complete",
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

