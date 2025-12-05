"use client";

import { motion } from "framer-motion";
import { Zap, ArrowLeftRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentRole } from "./AgentCardV2";

interface Tension {
  description: string;
  lane_a_position: string;
  lane_b_position: string;
  resolution: "defer_to_clinical" | "defer_to_exploration" | "unresolved" | "context_dependent";
  resolution_rationale?: string;
  what_would_resolve?: string;
  // Sometimes tensions are between specific agents
  agent_a?: AgentRole;
  agent_b?: AgentRole;
}

interface TensionsPanelProps {
  tensions: Tension[];
  className?: string;
}

const AGENT_COLORS: Record<AgentRole, string> = {
  empiricist: "var(--agent-empiricist)",
  skeptic: "var(--agent-skeptic)",
  mechanist: "var(--agent-mechanist)",
  speculator: "var(--agent-speculator)",
  pragmatist: "var(--agent-pragmatist)",
  patient_voice: "var(--agent-patient-voice)",
  arbitrator: "var(--agent-arbitrator)",
  advocate: "var(--agent-advocate)",
};

const RESOLUTION_LABELS: Record<Tension["resolution"], string> = {
  defer_to_clinical: "Deferred to Clinical Lane",
  defer_to_exploration: "Deferred to Exploratory Lane",
  unresolved: "Unresolved",
  context_dependent: "Context Dependent",
};

function TensionCard({ tension, index }: { tension: Tension; index: number }) {
  const agentALabel = tension.agent_a 
    ? tension.agent_a.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())
    : "Lane A";
  const agentBLabel = tension.agent_b
    ? tension.agent_b.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())
    : "Lane B";
  
  const agentAColor = tension.agent_a 
    ? AGENT_COLORS[tension.agent_a] 
    : "var(--lane-a-primary)";
  const agentBColor = tension.agent_b 
    ? AGENT_COLORS[tension.agent_b] 
    : "var(--lane-b-primary)";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="rounded-lg border border-amber-500/30 bg-amber-900/10 p-5"
    >
      {/* Header with vs. styling */}
      <div className="flex items-center justify-center gap-4 mb-4">
        <span 
          className="font-semibold"
          style={{ color: agentAColor }}
        >
          {agentALabel}
        </span>
        <ArrowLeftRight className="w-5 h-5 text-amber-400" />
        <span 
          className="font-semibold"
          style={{ color: agentBColor }}
        >
          {agentBLabel}
        </span>
      </div>
      
      {/* Divider */}
      <div className="h-px bg-amber-500/30 mb-4" />
      
      {/* Nature of Tension */}
      <div className="mb-4">
        <h4 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Nature</h4>
        <p className="text-sm text-slate-300 leading-relaxed">
          {tension.description}
        </p>
      </div>
      
      {/* Positions */}
      {(tension.lane_a_position || tension.lane_b_position) && (
        <div className="grid grid-cols-2 gap-4 mb-4">
          {tension.lane_a_position && (
            <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
              <span className="text-xs text-emerald-400 font-medium block mb-1">
                {agentALabel}&apos;s Position
              </span>
              <p className="text-xs text-slate-400">{tension.lane_a_position}</p>
            </div>
          )}
          {tension.lane_b_position && (
            <div className="p-3 rounded-lg bg-purple-500/5 border border-purple-500/20">
              <span className="text-xs text-purple-400 font-medium block mb-1">
                {agentBLabel}&apos;s Position
              </span>
              <p className="text-xs text-slate-400">{tension.lane_b_position}</p>
            </div>
          )}
        </div>
      )}
      
      {/* Resolution Status */}
      {tension.resolution_rationale && (
        <div className="mb-4">
          <h4 className="text-xs text-slate-500 uppercase tracking-wider mb-2">
            Resolution Attempted
          </h4>
          <p className="text-sm text-slate-400">{tension.resolution_rationale}</p>
        </div>
      )}
      
      {/* What Would Resolve */}
      {tension.what_would_resolve && (
        <div className="p-3 rounded-lg bg-cyan-500/5 border border-cyan-500/20">
          <h4 className="text-xs text-cyan-400 font-medium mb-1">
            What Would Resolve This
          </h4>
          <p className="text-xs text-slate-300">{tension.what_would_resolve}</p>
        </div>
      )}
    </motion.div>
  );
}

export function TensionsPanel({ tensions, className }: TensionsPanelProps) {
  if (tensions.length === 0) {
    return null;
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-center gap-2">
        <Zap className="w-5 h-5 text-amber-400" />
        <h3 className="font-semibold text-slate-200">Tensions</h3>
        <span className="text-xs text-slate-500">
          ({tensions.length} unresolved disagreement{tensions.length !== 1 ? "s" : ""})
        </span>
      </div>
      
      {/* Tension Cards */}
      <div className="space-y-4">
        {tensions.map((tension, idx) => (
          <TensionCard key={idx} tension={tension} index={idx} />
        ))}
      </div>
    </div>
  );
}

