"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Swords, 
  ChevronDown, 
  ArrowRight,
  AlertTriangle,
  AlertCircle,
  Zap,
  Info
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { AgentRole } from "./AgentCardV2";

type CritiqueSeverity = "critical" | "major" | "moderate" | "minor";

interface Critique {
  critic_role: AgentRole;
  target_role: AgentRole;
  target_lane: "A" | "B";
  critique_type: "safety" | "feasibility" | "stagnation" | "mechanism";
  content: string;
  severity: CritiqueSeverity;
}

interface CrossExaminationPanelProps {
  critiques: Critique[];
  isLoading?: boolean;
  className?: string;
}

const SEVERITY_CONFIG: Record<CritiqueSeverity, {
  icon: React.ReactNode;
  label: string;
  color: string;
  bgColor: string;
}> = {
  critical: {
    icon: <AlertCircle className="w-4 h-4" />,
    label: "CRITICAL",
    color: "#ef4444",
    bgColor: "rgba(239, 68, 68, 0.15)",
  },
  major: {
    icon: <AlertTriangle className="w-4 h-4" />,
    label: "MAJOR",
    color: "#f59e0b",
    bgColor: "rgba(245, 158, 11, 0.15)",
  },
  moderate: {
    icon: <Zap className="w-4 h-4" />,
    label: "MODERATE",
    color: "#facc15",
    bgColor: "rgba(250, 204, 21, 0.15)",
  },
  minor: {
    icon: <Info className="w-4 h-4" />,
    label: "MINOR",
    color: "#64748b",
    bgColor: "rgba(100, 116, 139, 0.15)",
  },
};

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

function CritiqueCard({ critique }: { critique: Critique }) {
  const severityConfig = SEVERITY_CONFIG[critique.severity];
  const criticColor = AGENT_COLORS[critique.critic_role];
  const targetColor = AGENT_COLORS[critique.target_role];
  
  const criticLabel = critique.critic_role.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  const targetLabel = critique.target_role.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());

  return (
    <div 
      className="critique-card rounded-lg border border-slate-700/50 bg-slate-800/30 p-4"
      data-severity={critique.severity}
    >
      {/* Header: Critic → Target */}
      <div className="flex items-center gap-2 mb-3">
        <span 
          className="flex items-center gap-1.5"
          style={{ color: criticColor }}
        >
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: criticColor }} />
          <span className="font-medium text-sm">{criticLabel}</span>
        </span>
        <ArrowRight className="w-4 h-4 text-slate-500" />
        <span 
          className="text-sm"
          style={{ color: targetColor }}
        >
          {targetLabel}
        </span>
      </div>
      
      {/* Critique Content */}
      <blockquote className="text-sm text-slate-300 leading-relaxed mb-3 pl-3 border-l-2 border-slate-600 italic">
        &ldquo;{critique.content}&rdquo;
      </blockquote>
      
      {/* Severity Badge */}
      <div 
        className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium"
        style={{ 
          backgroundColor: severityConfig.bgColor,
          color: severityConfig.color,
        }}
      >
        {severityConfig.icon}
        <span>Severity: {severityConfig.label}</span>
      </div>
    </div>
  );
}

export function CrossExaminationPanel({
  critiques,
  isLoading = false,
  className,
}: CrossExaminationPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Separate critiques by direction
  const laneACritiquesLaneB = critiques.filter(c => 
    ["empiricist", "skeptic", "pragmatist", "patient_voice"].includes(c.critic_role) &&
    c.target_lane === "B"
  );
  const laneBCritiquesLaneA = critiques.filter(c => 
    ["mechanist", "speculator"].includes(c.critic_role) &&
    c.target_lane === "A"
  );

  if (critiques.length === 0 && !isLoading) {
    return null;
  }

  return (
    <div className={cn(
      "rounded-lg border border-slate-700/50 bg-slate-800/20 overflow-hidden",
      className
    )}>
      {/* Header */}
      <button
        className="w-full flex items-center justify-between p-4 hover:bg-white/[0.02] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-red-500/10">
            <Swords className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-left">
            <h3 className="font-medium text-slate-200">Cross-Examination</h3>
            <p className="text-xs text-slate-400">
              {critiques.length} critiques between lanes
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Severity summary */}
          {critiques.some(c => c.severity === "critical") && (
            <Badge className="bg-red-500/20 text-red-300 text-xs">
              Critical
            </Badge>
          )}
          {critiques.some(c => c.severity === "major") && (
            <Badge className="bg-orange-500/20 text-orange-300 text-xs">
              Major
            </Badge>
          )}
          
          <ChevronDown className={cn(
            "w-4 h-4 text-slate-400 transition-transform",
            isExpanded && "rotate-180"
          )} />
        </div>
      </button>
      
      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-4 pb-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 relative">
                {/* Animated arrows in the middle (desktop only) */}
                <div className="hidden lg:flex absolute left-1/2 top-0 bottom-0 -translate-x-1/2 flex-col items-center justify-center gap-4 z-10">
                  <ArrowRight className="w-5 h-5 text-emerald-400 arrow-right" />
                  <ArrowRight className="w-5 h-5 text-purple-400 arrow-left rotate-180" />
                </div>
                
                {/* Lane A → Lane B */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-emerald-400 mb-2">
                    <span className="text-xs font-medium uppercase tracking-wider">
                      Lane A → Lane B
                    </span>
                    <span className="text-xs text-slate-500">(Safety & Feasibility)</span>
                  </div>
                  
                  {laneACritiquesLaneB.length > 0 ? (
                    laneACritiquesLaneB.map((critique, idx) => (
                      <CritiqueCard key={idx} critique={critique} />
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 italic">
                      No critiques from Lane A
                    </p>
                  )}
                </div>
                
                {/* Lane B → Lane A */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-purple-400 mb-2">
                    <span className="text-xs font-medium uppercase tracking-wider">
                      Lane B → Lane A
                    </span>
                    <span className="text-xs text-slate-500">(Stagnation & Mechanism)</span>
                  </div>
                  
                  {laneBCritiquesLaneA.length > 0 ? (
                    laneBCritiquesLaneA.map((critique, idx) => (
                      <CritiqueCard key={idx} critique={critique} />
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 italic">
                      No critiques from Lane B
                    </p>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

