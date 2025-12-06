/**
 * Shared agent configuration and metadata.
 * 
 * This module provides a single source of truth for agent roles,
 * colors, icons, and descriptions used across the application.
 */

import {
  Heart,
  FlaskConical,
  Cog,
  AlertTriangle,
  User,
  Scale,
  Brain,
  Lightbulb,
  DollarSign,
  type LucideIcon,
} from "lucide-react";

/**
 * All possible agent roles in the system.
 */
export type AgentRole =
  | "advocate"
  | "empiricist"
  | "mechanist"
  | "skeptic"
  | "patient_voice"
  | "arbitrator"
  | "speculator"
  | "pragmatist";

/**
 * Agent state during conference execution.
 */
export type AgentState = "idle" | "waiting" | "thinking" | "streaming" | "complete" | "error";

/**
 * Configuration for a single agent role.
 */
export interface AgentMeta {
  /** Display name */
  label: string;
  /** Brief description of the agent's focus */
  description: string;
  /** Lucide icon component */
  icon: LucideIcon;
  /** Primary color (Tailwind class without prefix) */
  color: string;
  /** CSS variable for theming */
  cssVar: string;
  /** Gradient for card backgrounds */
  gradient: string;
  /** Glow color for active state */
  glow: "cyan" | "purple" | "green" | "red" | "yellow" | "orange" | "none";
  /** Which lane this agent belongs to (for v2/v3) */
  lane: "A" | "B" | "synthesis";
}

/**
 * Complete agent configuration mapping.
 * Single source of truth for all agent metadata.
 */
export const AGENT_CONFIG: Record<AgentRole, AgentMeta> = {
  advocate: {
    label: "Advocate",
    description: "Patient-centered outcomes focus",
    icon: Heart,
    color: "green-400",
    cssVar: "var(--agent-advocate)",
    gradient: "from-green-500/20 to-transparent",
    glow: "green",
    lane: "A",
  },
  empiricist: {
    label: "Empiricist",
    description: "Evidence-based reasoning",
    icon: FlaskConical,
    color: "blue-400",
    cssVar: "var(--agent-empiricist)",
    gradient: "from-blue-500/20 to-transparent",
    glow: "cyan",
    lane: "A",
  },
  mechanist: {
    label: "Mechanist",
    description: "Pathophysiology focus",
    icon: Cog,
    color: "purple-400",
    cssVar: "var(--agent-mechanist)",
    gradient: "from-purple-500/20 to-transparent",
    glow: "purple",
    lane: "B",
  },
  skeptic: {
    label: "Skeptic",
    description: "Challenges assumptions",
    icon: AlertTriangle,
    color: "red-400",
    cssVar: "var(--agent-skeptic)",
    gradient: "from-red-500/20 to-transparent",
    glow: "red",
    lane: "A",
  },
  patient_voice: {
    label: "Patient Voice",
    description: "Patient perspective",
    icon: User,
    color: "yellow-400",
    cssVar: "var(--agent-patient-voice)",
    gradient: "from-yellow-500/20 to-transparent",
    glow: "yellow",
    lane: "A",
  },
  arbitrator: {
    label: "Arbitrator",
    description: "Synthesizes consensus",
    icon: Scale,
    color: "cyan-400",
    cssVar: "var(--agent-arbitrator)",
    gradient: "from-cyan-500/20 to-transparent",
    glow: "cyan",
    lane: "synthesis",
  },
  speculator: {
    label: "Speculator",
    description: "Creative hypotheses",
    icon: Lightbulb,
    color: "orange-400",
    cssVar: "var(--agent-speculator)",
    gradient: "from-orange-500/20 to-transparent",
    glow: "orange",
    lane: "B",
  },
  pragmatist: {
    label: "Pragmatist",
    description: "Healthcare feasibility",
    icon: DollarSign,
    color: "emerald-400",
    cssVar: "var(--agent-pragmatist)",
    gradient: "from-emerald-500/20 to-transparent",
    glow: "green",
    lane: "A",
  },
};

/**
 * Get agent metadata, with fallback for unknown roles.
 */
export function getAgentMeta(role: string): AgentMeta {
  const normalizedRole = role.toLowerCase() as AgentRole;
  return AGENT_CONFIG[normalizedRole] || {
    label: role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    description: "Unknown agent",
    icon: Brain,
    color: "slate-400",
    cssVar: "var(--agent-unknown)",
    gradient: "from-slate-500/20 to-transparent",
    glow: "none" as const,
    lane: "A" as const,
  };
}

/**
 * Get agents by lane.
 */
export function getAgentsByLane(lane: "A" | "B" | "synthesis"): AgentRole[] {
  return (Object.entries(AGENT_CONFIG) as [AgentRole, AgentMeta][])
    .filter(([, meta]) => meta.lane === lane)
    .map(([role]) => role);
}

/**
 * Lane A (Clinical) agent roles.
 */
export const LANE_A_AGENTS = getAgentsByLane("A");

/**
 * Lane B (Exploratory) agent roles.
 */
export const LANE_B_AGENTS = getAgentsByLane("B");

/**
 * All agent roles as an array.
 */
export const ALL_AGENT_ROLES = Object.keys(AGENT_CONFIG) as AgentRole[];

