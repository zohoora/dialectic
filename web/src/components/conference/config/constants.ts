/**
 * Constants for conference configuration.
 */

import { 
  Sliders, Search, Shield, Beaker, AlertTriangle 
} from "lucide-react";
import type { 
  ConferenceMode, TopologyType, AgentRoleKey, AgentInfo, 
  ModelOption, LibrarianModelOption, V3ModelConfig, ConferenceConfig 
} from "./types";

// Mode options for the conference
export const MODE_OPTIONS: Array<{
  value: ConferenceMode;
  label: string;
  description: string;
  icon: React.ElementType;
  color: string;
}> = [
  { 
    value: "auto", 
    label: "Auto (Router decides)", 
    description: "Recommended - system analyzes query complexity",
    icon: Sliders,
    color: "text-cyan-400",
  },
  { 
    value: "STANDARD_CARE", 
    label: "Standard Care", 
    description: "Guideline check, minimal deliberation",
    icon: Shield,
    color: "text-slate-400",
  },
  { 
    value: "COMPLEX_DILEMMA", 
    label: "Complex Dilemma", 
    description: "Full team, all lanes",
    icon: AlertTriangle,
    color: "text-amber-400",
  },
  { 
    value: "NOVEL_RESEARCH", 
    label: "Novel Research", 
    description: "Emphasis on Speculator",
    icon: Beaker,
    color: "text-purple-400",
  },
  { 
    value: "DIAGNOSTIC_PUZZLE", 
    label: "Diagnostic Puzzle", 
    description: "Emphasis on differentials",
    icon: Search,
    color: "text-blue-400",
  },
];

// Topology options for deliberation structure
export const TOPOLOGY_OPTIONS: Array<{
  value: TopologyType;
  label: string;
  description: string;
  icon: React.ElementType;
  color: string;
}> = [
  {
    value: "auto",
    label: "Auto (Router decides)",
    description: "System selects best topology for the query",
    icon: Sliders,
    color: "text-cyan-400",
  },
  {
    value: "free_discussion",
    label: "Free Discussion",
    description: "Open multi-agent deliberation",
    icon: AlertTriangle,
    color: "text-slate-400",
  },
  {
    value: "oxford_debate",
    label: "Oxford Debate",
    description: "Structured pro/con for binary decisions",
    icon: Shield,
    color: "text-green-400",
  },
  {
    value: "delphi_method",
    label: "Delphi Method",
    description: "Anonymous rounds to reduce anchoring",
    icon: Beaker,
    color: "text-orange-400",
  },
  {
    value: "socratic_spiral",
    label: "Socratic Spiral",
    description: "Questions-first for diagnostic uncertainty",
    icon: Search,
    color: "text-blue-400",
  },
  {
    value: "red_team_blue_team",
    label: "Red Team",
    description: "Adversarial stress-testing for high-stakes",
    icon: Shield,
    color: "text-red-400",
  },
];

// Timeframe options for Scout literature search
export const TIMEFRAME_OPTIONS = [
  { value: "6_months", label: "Last 6 months" },
  { value: "12_months", label: "Last 12 months" },
  { value: "24_months", label: "Last 24 months" },
  { value: "all_time", label: "All time" },
] as const;

// Model options for system components
export const MODEL_OPTIONS: ModelOption[] = [
  // Fast/cheap models
  { value: "anthropic/claude-3-haiku", label: "Claude 3 Haiku", category: "fast" },
  { value: "openai/gpt-4o-mini", label: "GPT-4o Mini", category: "fast" },
  { value: "google/gemini-flash-1.5", label: "Gemini Flash 1.5", category: "fast" },
  // Balanced models
  { value: "openai/gpt-4o", label: "GPT-4o", category: "balanced" },
  { value: "anthropic/claude-sonnet-4", label: "Claude Sonnet 4", category: "balanced" },
  { value: "google/gemini-pro-1.5", label: "Gemini Pro 1.5", category: "balanced" },
  // Powerful models
  { value: "anthropic/claude-3.5-sonnet", label: "Claude 3.5 Sonnet", category: "powerful" },
  { value: "openai/gpt-4-turbo", label: "GPT-4 Turbo", category: "powerful" },
  { value: "anthropic/claude-3-opus", label: "Claude 3 Opus", category: "powerful" },
  // Deep reasoning models
  { value: "anthropic/claude-opus-4", label: "Claude Opus 4", category: "reasoning" },
  { value: "openai/o1-preview", label: "o1 Preview", category: "reasoning" },
  { value: "deepseek/deepseek-r1", label: "DeepSeek R1", category: "reasoning" },
];

// Component info for model selection
export const MODEL_COMPONENT_INFO: Record<keyof V3ModelConfig, {
  label: string;
  description: string;
  recommendation: string;
}> = {
  router_model: {
    label: "Router Model",
    description: "Analyzes query to select conference mode and topology",
    recommendation: "Use a balanced model for accurate routing",
  },
  classifier_model: {
    label: "Classifier Model",
    description: "Categorizes queries for learning and heuristic retrieval",
    recommendation: "Fast model recommended (high volume, low complexity)",
  },
  surgeon_model: {
    label: "Surgeon Model",
    description: "Extracts generalizable heuristics from conferences",
    recommendation: "Powerful model recommended (nuanced extraction)",
  },
  scout_model: {
    label: "Scout Model",
    description: "Analyzes and summarizes literature findings (future)",
    recommendation: "Balanced model for synthesis",
  },
  validator_model: {
    label: "Validator Model",
    description: "Validates speculations against new evidence",
    recommendation: "Balanced model for accurate validation",
  },
};

// Agent model options (for individual agent configuration)
export const AGENT_MODEL_OPTIONS: ModelOption[] = [
  { value: "anthropic/claude-sonnet-4", label: "Claude Sonnet 4", category: "balanced" },
  { value: "openai/gpt-4o", label: "GPT-4o", category: "balanced" },
  { value: "anthropic/claude-3.5-sonnet", label: "Claude 3.5 Sonnet", category: "powerful" },
  { value: "openai/gpt-4-turbo", label: "GPT-4 Turbo", category: "powerful" },
  { value: "anthropic/claude-3-opus", label: "Claude 3 Opus", category: "powerful" },
  { value: "anthropic/claude-opus-4", label: "Claude Opus 4", category: "reasoning" },
  { value: "openai/o1-preview", label: "o1 Preview", category: "reasoning" },
  { value: "deepseek/deepseek-r1", label: "DeepSeek R1", category: "reasoning" },
  { value: "google/gemini-pro-1.5", label: "Gemini Pro 1.5", category: "balanced" },
];

// Agent information by role
export const AGENT_INFO: Record<AgentRoleKey, AgentInfo> = {
  empiricist: {
    label: "Empiricist",
    description: "Evidence-based reasoning from clinical trials",
    lane: "A",
    color: "text-green-400",
    bgColor: "bg-green-500/10",
  },
  skeptic: {
    label: "Skeptic",
    description: "Critical analysis, identifies risks and limitations",
    lane: "A",
    color: "text-amber-400",
    bgColor: "bg-amber-500/10",
  },
  mechanist: {
    label: "Mechanist",
    description: "Focuses on biological mechanisms and pathophysiology",
    lane: "B",
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
  },
  speculator: {
    label: "Speculator",
    description: "Generates novel hypotheses and creative solutions",
    lane: "B",
    color: "text-purple-400",
    bgColor: "bg-purple-500/10",
  },
  pragmatist: {
    label: "Pragmatist",
    description: "Evaluates real-world feasibility and implementation",
    lane: "A",
    color: "text-orange-400",
    bgColor: "bg-orange-500/10",
  },
  patient_voice: {
    label: "Patient Voice",
    description: "Represents patient preferences and quality of life",
    lane: "A",
    color: "text-pink-400",
    bgColor: "bg-pink-500/10",
  },
};

// Librarian model options (needs large context)
export const LIBRARIAN_MODEL_OPTIONS: LibrarianModelOption[] = [
  { value: "google/gemini-3-pro-preview", label: "Gemini 3 Pro (1M context)", recommended: true },
  { value: "google/gemini-pro-1.5", label: "Gemini Pro 1.5 (1M context)", recommended: true },
  { value: "anthropic/claude-sonnet-4", label: "Claude Sonnet 4 (200K)", recommended: false },
  { value: "anthropic/claude-3.5-sonnet", label: "Claude 3.5 Sonnet (200K)", recommended: false },
  { value: "anthropic/claude-3-opus", label: "Claude 3 Opus (200K)", recommended: false },
  { value: "openai/gpt-4o", label: "GPT-4o (128K)", recommended: false },
  { value: "openai/gpt-4-turbo", label: "GPT-4 Turbo (128K)", recommended: false },
];

// Default conference configuration
export const DEFAULT_CONFIG: ConferenceConfig = {
  riskTolerance: 0.5,
  modeOverride: "auto",
  topologyOverride: "auto",
  enableScout: true,
  scoutTimeframe: "12_months",
  enableFragilityTesting: false,
  fragilityTests: 5,
  enableLearning: true,
  modelConfig: {
    router_model: "openai/gpt-4o",
    classifier_model: "anthropic/claude-3-haiku",
    surgeon_model: "anthropic/claude-sonnet-4",
    scout_model: "openai/gpt-4o",
    validator_model: "openai/gpt-4o",
  },
  agents: [
    { role: "empiricist", enabled: true, model: "anthropic/claude-sonnet-4" },
    { role: "skeptic", enabled: true, model: "anthropic/claude-sonnet-4" },
    { role: "mechanist", enabled: true, model: "anthropic/claude-sonnet-4" },
    { role: "speculator", enabled: true, model: "anthropic/claude-sonnet-4" },
    { role: "pragmatist", enabled: true, model: "anthropic/claude-sonnet-4" },
    { role: "patient_voice", enabled: true, model: "anthropic/claude-sonnet-4" },
  ],
  librarian: {
    model: "google/gemini-3-pro-preview",
    maxQueriesPerTurn: 3,
  },
};

