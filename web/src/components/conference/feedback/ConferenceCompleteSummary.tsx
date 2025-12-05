"use client";

import { motion } from "framer-motion";
import { Check, Clock, Coins, FileText, Shield, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

// ============================================================================
// TYPES
// ============================================================================

interface PhaseBreakdown {
  name: string;
  duration: number; // milliseconds
  percentage: number; // 0-100
}

interface ConferenceCompleteSummaryProps {
  totalDuration: number; // milliseconds
  phases: PhaseBreakdown[];
  tokensUsed: {
    input: number;
    output: number;
    total: number;
  };
  citationsVerified?: {
    verified: number;
    total: number;
  };
  fragilitySurvivalRate?: {
    survived: number;
    total: number;
  };
  onViewResults: () => void;
  autoScrollDelay?: number; // milliseconds
}

// ============================================================================
// PHASE BREAKDOWN BAR
// ============================================================================

interface PhaseBarProps {
  phase: PhaseBreakdown;
  maxDuration: number;
}

function PhaseBar({ phase, maxDuration }: PhaseBarProps) {
  const widthPercent = (phase.duration / maxDuration) * 100;
  
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-28 text-slate-400 truncate">{phase.name}</span>
      <div className="flex-1 h-2 bg-slate-700/50 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-cyan-500 to-violet-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${widthPercent}%` }}
          transition={{ duration: 0.5, delay: 0.1 }}
        />
      </div>
      <span className="w-12 text-right text-slate-300 font-mono">
        {(phase.duration / 1000).toFixed(1)}s
      </span>
    </div>
  );
}

// ============================================================================
// STAT CARD
// ============================================================================

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  subValue?: string;
  variant?: "default" | "success" | "warning";
}

function StatCard({ icon, label, value, subValue, variant = "default" }: StatCardProps) {
  return (
    <div className={cn(
      "rounded-lg border p-4 space-y-2",
      variant === "default" && "border-slate-700/50 bg-slate-800/30",
      variant === "success" && "border-green-500/30 bg-green-500/5",
      variant === "warning" && "border-amber-500/30 bg-amber-500/5"
    )}>
      <div className="flex items-center gap-2 text-slate-400">
        {icon}
        <span className="text-xs uppercase tracking-wider">{label}</span>
      </div>
      <div>
        <span className={cn(
          "text-xl font-semibold",
          variant === "default" && "text-slate-200",
          variant === "success" && "text-green-400",
          variant === "warning" && "text-amber-400"
        )}>
          {value}
        </span>
        {subValue && (
          <span className="text-xs text-slate-500 ml-2">{subValue}</span>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// CONFERENCE COMPLETE SUMMARY
// ============================================================================

export function ConferenceCompleteSummary({
  totalDuration,
  phases,
  tokensUsed,
  citationsVerified,
  fragilitySurvivalRate,
  onViewResults,
  autoScrollDelay = 2000,
}: ConferenceCompleteSummaryProps) {
  const maxDuration = Math.max(...phases.map(p => p.duration));
  const totalSeconds = totalDuration / 1000;

  // Auto-scroll effect would be handled by parent component
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg border border-green-500/30 bg-slate-800/30 overflow-hidden"
    >
      {/* Header */}
      <div className="bg-green-500/10 border-b border-green-500/30 px-6 py-4">
        <div className="flex items-center justify-center gap-3">
          <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
            <Check className="w-5 h-5 text-green-400" />
          </div>
          <span className="text-xl font-semibold text-green-400">
            CONFERENCE COMPLETE
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Total Time */}
        <div className="text-center">
          <span className="text-3xl font-bold text-slate-100">
            {totalSeconds.toFixed(1)}
          </span>
          <span className="text-lg text-slate-400 ml-2">seconds</span>
        </div>

        {/* Phase Breakdown */}
        <div className="space-y-3">
          <h3 className="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-2">
            <Clock className="w-3 h-3" />
            Phase Breakdown
          </h3>
          <div className="space-y-2">
            {phases.map((phase, idx) => (
              <PhaseBar key={idx} phase={phase} maxDuration={maxDuration} />
            ))}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            icon={<FileText className="w-3.5 h-3.5" />}
            label="Tokens Used"
            value={tokensUsed.total.toLocaleString()}
            subValue={`${tokensUsed.input.toLocaleString()} in / ${tokensUsed.output.toLocaleString()} out`}
          />
          
          {citationsVerified && (
            <StatCard
              icon={<Check className="w-3.5 h-3.5" />}
              label="Citations"
              value={`${citationsVerified.verified}/${citationsVerified.total}`}
              subValue={`${Math.round((citationsVerified.verified / citationsVerified.total) * 100)}% verified`}
              variant={citationsVerified.verified / citationsVerified.total >= 0.8 ? "success" : "warning"}
            />
          )}
          
          {fragilitySurvivalRate && (
            <StatCard
              icon={<Shield className="w-3.5 h-3.5" />}
              label="Fragility"
              value={`${fragilitySurvivalRate.survived}/${fragilitySurvivalRate.total}`}
              subValue={`${Math.round((fragilitySurvivalRate.survived / fragilitySurvivalRate.total) * 100)}% survival`}
              variant={fragilitySurvivalRate.survived / fragilitySurvivalRate.total >= 0.75 ? "success" : "warning"}
            />
          )}
          
          <StatCard
            icon={<Coins className="w-3.5 h-3.5" />}
            label="Est. Cost"
            value={`$${((tokensUsed.total / 1000) * 0.003).toFixed(4)}`}
            subValue="approximate"
          />
        </div>

        {/* View Results Button */}
        <div className="flex justify-center pt-4">
          <Button
            onClick={onViewResults}
            className="bg-gradient-to-r from-cyan-500 to-violet-500 text-white hover:opacity-90"
            size="lg"
          >
            <ArrowDown className="w-4 h-4 mr-2" />
            View Results
          </Button>
        </div>
      </div>
    </motion.div>
  );
}

// ============================================================================
// DEFAULT PHASES FOR DEMO
// ============================================================================

export const DEMO_PHASE_BREAKDOWN: PhaseBreakdown[] = [
  { name: "Routing", duration: 2100, percentage: 4 },
  { name: "Scout", duration: 8300, percentage: 18 },
  { name: "Lane A (4 agents)", duration: 18200, percentage: 39 },
  { name: "Lane B (2 agents)", duration: 12100, percentage: 26 },
  { name: "Cross-examination", duration: 8400, percentage: 18 },
  { name: "Synthesis", duration: 12800, percentage: 27 },
  { name: "Fragility testing", duration: 16400, percentage: 35 },
];

