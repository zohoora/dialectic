/**
 * Type definitions for conference configuration.
 */

export type ConferenceMode = 
  | "auto" 
  | "STANDARD_CARE" 
  | "COMPLEX_DILEMMA" 
  | "NOVEL_RESEARCH" 
  | "DIAGNOSTIC_PUZZLE";

export type TopologyType =
  | "auto"
  | "free_discussion"
  | "oxford_debate"
  | "delphi_method"
  | "socratic_spiral"
  | "red_team_blue_team";

export interface V3ModelConfig {
  router_model: string;
  classifier_model: string;
  surgeon_model: string;
  scout_model: string;
  validator_model: string;
}

export type AgentRoleKey = 
  | "empiricist"
  | "skeptic"
  | "mechanist"
  | "speculator"
  | "pragmatist"
  | "patient_voice";

export interface AgentConfig {
  role: AgentRoleKey;
  enabled: boolean;
  model: string;
}

export interface LibrarianConfig {
  model: string;
  maxQueriesPerTurn: number;
}

export interface ConferenceConfig {
  riskTolerance: number;
  modeOverride: ConferenceMode;
  topologyOverride: TopologyType;
  enableScout: boolean;
  scoutTimeframe: "6_months" | "12_months" | "24_months" | "all_time";
  enableFragilityTesting: boolean;
  fragilityTests: number;
  enableLearning: boolean;
  modelConfig: V3ModelConfig;
  agents: AgentConfig[];
  librarian: LibrarianConfig;
}

export interface ConfigPanelProps {
  config: ConferenceConfig;
  onChange: (config: ConferenceConfig) => void;
  disabled?: boolean;
  hasFiles?: boolean;
}

export interface AgentInfo {
  label: string;
  description: string;
  lane: "A" | "B";
  color: string;
  bgColor: string;
}

export interface ModelOption {
  value: string;
  label: string;
  category: "fast" | "balanced" | "powerful" | "reasoning";
}

export interface LibrarianModelOption {
  value: string;
  label: string;
  recommended: boolean;
}

