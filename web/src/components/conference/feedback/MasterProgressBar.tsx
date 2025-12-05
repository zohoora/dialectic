"use client";

import { motion } from "framer-motion";
import { Check, Loader2, Circle, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

// ============================================================================
// TYPES
// ============================================================================

export type PhaseStatus = "pending" | "running" | "complete" | "error";

export interface Phase {
  key: string;
  label: string;
  status: PhaseStatus;
  duration?: number; // milliseconds
  estimatedDuration?: number; // milliseconds
}

interface MasterProgressBarProps {
  phases: Phase[];
  currentPhase?: string;
  overallProgress: number; // 0-100
  estimatedTimeRemaining?: number; // seconds
  isComplete?: boolean;
  error?: string;
}

// ============================================================================
// PHASE INDICATOR
// ============================================================================

interface PhaseIndicatorProps {
  phase: Phase;
  isActive: boolean;
}

function PhaseIndicator({ phase, isActive }: PhaseIndicatorProps) {
  const getIcon = () => {
    switch (phase.status) {
      case "complete":
        return <Check className="w-3 h-3 text-green-400" />;
      case "running":
        return <Loader2 className="w-3 h-3 text-cyan-400 animate-spin" />;
      case "error":
        return <AlertCircle className="w-3 h-3 text-red-400" />;
      default:
        return <Circle className="w-3 h-3 text-slate-500" />;
    }
  };

  const getTimeDisplay = () => {
    if (phase.duration) {
      return `(${(phase.duration / 1000).toFixed(1)}s)`;
    }
    if (phase.status === "running" && phase.estimatedDuration) {
      return `(~${(phase.estimatedDuration / 1000).toFixed(0)}s)`;
    }
    if (phase.status === "pending" && phase.estimatedDuration) {
      return `(~${(phase.estimatedDuration / 1000).toFixed(0)}s)`;
    }
    return null;
  };

  return (
    <div 
      className={cn(
        "flex flex-col items-center gap-1 px-2 py-1 rounded-md transition-colors",
        isActive && "bg-cyan-500/10"
      )}
    >
      <div className="flex items-center gap-1.5">
        {getIcon()}
        <span className={cn(
          "text-xs font-medium",
          phase.status === "complete" && "text-green-400",
          phase.status === "running" && "text-cyan-400",
          phase.status === "error" && "text-red-400",
          phase.status === "pending" && "text-slate-500"
        )}>
          {phase.label}
        </span>
      </div>
      {getTimeDisplay() && (
        <span className="text-[10px] text-slate-500">
          {getTimeDisplay()}
        </span>
      )}
    </div>
  );
}

// ============================================================================
// MASTER PROGRESS BAR
// ============================================================================

export function MasterProgressBar({
  phases,
  currentPhase,
  overallProgress,
  estimatedTimeRemaining,
  isComplete,
  error,
}: MasterProgressBarProps) {
  const completedPhases = phases.filter(p => p.status === "complete").length;
  const totalPhases = phases.length;

  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={cn(
            "text-sm font-medium",
            isComplete ? "text-green-400" : error ? "text-red-400" : "text-slate-200"
          )}>
            {isComplete 
              ? "CONFERENCE COMPLETE" 
              : error 
                ? "CONFERENCE ERROR" 
                : "CONFERENCE IN PROGRESS"
            }
          </span>
          {!isComplete && !error && (
            <span className="text-xs text-slate-500">
              ({completedPhases}/{totalPhases} phases)
            </span>
          )}
        </div>
        
        {estimatedTimeRemaining !== undefined && !isComplete && !error && (
          <span className="text-xs text-slate-400">
            Est. ~{estimatedTimeRemaining}s left
          </span>
        )}
        
        {isComplete && (
          <span className="text-xs text-green-400">
            {overallProgress}% complete
          </span>
        )}
      </div>

      {/* Progress Bar */}
      <div className="relative h-2 bg-slate-700/50 rounded-full overflow-hidden">
        <motion.div
          className={cn(
            "absolute inset-y-0 left-0 rounded-full",
            error 
              ? "bg-red-500" 
              : isComplete 
                ? "bg-green-500" 
                : "bg-gradient-to-r from-cyan-500 to-violet-500"
          )}
          initial={{ width: 0 }}
          animate={{ width: `${overallProgress}%` }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        />
        {!isComplete && !error && (
          <div className="absolute inset-0 shimmer" />
        )}
      </div>

      {/* Phase Indicators */}
      <div className="flex items-center justify-between overflow-x-auto pb-1">
        {phases.map((phase) => (
          <PhaseIndicator
            key={phase.key}
            phase={phase}
            isActive={currentPhase === phase.key}
          />
        ))}
      </div>

      {/* Error Message */}
      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 rounded-md p-3">
          {error}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// DEFAULT PHASES
// ============================================================================

export const DEFAULT_V2_PHASES: Phase[] = [
  { key: "routing", label: "Route", status: "pending", estimatedDuration: 2000 },
  { key: "scout", label: "Scout", status: "pending", estimatedDuration: 8000 },
  { key: "lane_a", label: "Lane A", status: "pending", estimatedDuration: 20000 },
  { key: "lane_b", label: "Lane B", status: "pending", estimatedDuration: 15000 },
  { key: "cross_exam", label: "Cross", status: "pending", estimatedDuration: 8000 },
  { key: "synthesis", label: "Synth", status: "pending", estimatedDuration: 12000 },
  { key: "fragility", label: "Test", status: "pending", estimatedDuration: 15000 },
];

// ============================================================================
// UTILITY: Calculate Progress
// ============================================================================

export function calculateOverallProgress(phases: Phase[]): number {
  if (phases.length === 0) return 0;
  
  let totalWeight = 0;
  let completedWeight = 0;
  
  phases.forEach(phase => {
    const weight = phase.estimatedDuration || 5000;
    totalWeight += weight;
    
    if (phase.status === "complete") {
      completedWeight += weight;
    } else if (phase.status === "running") {
      // Assume 50% complete if running
      completedWeight += weight * 0.5;
    }
  });
  
  return Math.round((completedWeight / totalWeight) * 100);
}

export function estimateTimeRemaining(phases: Phase[]): number {
  let remaining = 0;
  
  phases.forEach(phase => {
    if (phase.status === "pending") {
      remaining += (phase.estimatedDuration || 5000) / 1000;
    } else if (phase.status === "running") {
      remaining += ((phase.estimatedDuration || 5000) / 1000) * 0.5;
    }
  });
  
  return Math.round(remaining);
}

