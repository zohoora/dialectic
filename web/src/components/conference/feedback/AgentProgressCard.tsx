"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { 
  ChevronDown, 
  ChevronUp, 
  Eye,
  ExternalLink,
  Check,
  Loader2,
  AlertCircle,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

// ============================================================================
// TYPES
// ============================================================================

export type AgentStatus = "waiting" | "generating" | "complete" | "error";

export type AgentRole = 
  | "empiricist" 
  | "skeptic" 
  | "mechanist" 
  | "speculator" 
  | "pragmatist" 
  | "patient_voice"
  | "arbitrator"
  | "advocate";

interface AgentProgressCardProps {
  role: AgentRole;
  status: AgentStatus;
  tokensGenerated: number;
  tokensEstimated: number;
  elapsedTime: number; // seconds
  estimatedTimeRemaining?: number; // seconds
  liveOutput?: string;
  confidence?: number;
  onExpand?: () => void;
  onViewRaw?: () => void;
  lane?: "A" | "B";
  compact?: boolean;
}

// ============================================================================
// CONSTANTS
// ============================================================================

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

const AGENT_LABELS: Record<AgentRole, string> = {
  empiricist: "EMPIRICIST",
  skeptic: "SKEPTIC",
  mechanist: "MECHANIST",
  speculator: "SPECULATOR",
  pragmatist: "PRAGMATIST",
  patient_voice: "PATIENT VOICE",
  arbitrator: "ARBITRATOR",
  advocate: "ADVOCATE",
};

// ============================================================================
// TOKEN PROGRESS BAR
// ============================================================================

interface TokenProgressBarProps {
  generated: number;
  estimated: number;
  color: string;
}

function TokenProgressBar({ generated, estimated, color }: TokenProgressBarProps) {
  const progress = estimated > 0 ? Math.min((generated / estimated) * 100, 100) : 0;
  
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">Progress</span>
        <span className="text-slate-300 font-mono">
          {generated} / ~{estimated} tokens
        </span>
      </div>
      <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.2 }}
        />
      </div>
    </div>
  );
}

// ============================================================================
// LIVE OUTPUT PREVIEW
// ============================================================================

interface LiveOutputPreviewProps {
  content: string;
  maxLines?: number;
}

function LiveOutputPreview({ content, maxLines = 4 }: LiveOutputPreviewProps) {
  // Truncate to last N lines
  const lines = content.split("\n");
  const displayLines = lines.slice(-maxLines);
  const truncated = displayLines.join("\n");
  
  return (
    <div className="rounded-md bg-slate-900/50 border border-slate-700/50 p-3">
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">
        Live Output
      </div>
      <div className="text-sm text-slate-300 font-mono whitespace-pre-wrap break-words">
        {truncated}
        <span className="inline-block w-2 h-4 bg-cyan-400 ml-0.5 animate-pulse" />
      </div>
    </div>
  );
}

// ============================================================================
// STATUS BADGE
// ============================================================================

interface StatusBadgeProps {
  status: AgentStatus;
}

function StatusBadge({ status }: StatusBadgeProps) {
  const config: Record<AgentStatus, { icon: React.ReactNode; label: string; className: string }> = {
    waiting: {
      icon: <Clock className="w-3 h-3" />,
      label: "Waiting",
      className: "bg-slate-500/20 text-slate-400 border-slate-500/30",
    },
    generating: {
      icon: <Loader2 className="w-3 h-3 animate-spin" />,
      label: "Generating",
      className: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
    },
    complete: {
      icon: <Check className="w-3 h-3" />,
      label: "Complete",
      className: "bg-green-500/20 text-green-400 border-green-500/30",
    },
    error: {
      icon: <AlertCircle className="w-3 h-3" />,
      label: "Error",
      className: "bg-red-500/20 text-red-400 border-red-500/30",
    },
  };

  const c = config[status];

  return (
    <div className={cn(
      "flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium border",
      c.className
    )}>
      {c.icon}
      {c.label}
    </div>
  );
}

// ============================================================================
// AGENT PROGRESS CARD
// ============================================================================

export function AgentProgressCard({
  role,
  status,
  tokensGenerated,
  tokensEstimated,
  elapsedTime,
  estimatedTimeRemaining,
  liveOutput,
  confidence,
  onExpand,
  onViewRaw,
  lane,
  compact = false,
}: AgentProgressCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const color = AGENT_COLORS[role];
  const label = AGENT_LABELS[role];

  const laneClass = lane === "A" 
    ? "border-l-2 border-l-green-500/50" 
    : lane === "B" 
      ? "border-l-2 border-l-purple-500/50"
      : "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-lg border border-slate-700/50 bg-slate-800/30 overflow-hidden",
        status === "generating" && "streaming",
        laneClass
      )}
      style={{ "--glow-color": color } as React.CSSProperties}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <span 
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: color }}
          />
          <span className="text-sm font-semibold uppercase tracking-wide" style={{ color }}>
            {label}
          </span>
        </div>
        <StatusBadge status={status} />
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Progress - show when generating */}
        {status === "generating" && (
          <>
            <TokenProgressBar 
              generated={tokensGenerated} 
              estimated={tokensEstimated}
              color={color}
            />
            
            <div className="flex justify-between text-xs text-slate-400">
              <span>{elapsedTime.toFixed(1)}s elapsed</span>
              {estimatedTimeRemaining !== undefined && (
                <span>Est. ~{estimatedTimeRemaining.toFixed(0)}s remaining</span>
              )}
            </div>

            {liveOutput && !compact && (
              <LiveOutputPreview content={liveOutput} />
            )}
          </>
        )}

        {/* Summary - show when complete */}
        {status === "complete" && (
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4 text-slate-400">
              <span>{tokensGenerated} tokens</span>
              {confidence !== undefined && (
                <span>Confidence: <span className="text-slate-200">{confidence}%</span></span>
              )}
            </div>
            <span className="text-slate-500">{elapsedTime.toFixed(1)}s</span>
          </div>
        )}

        {/* Waiting state */}
        {status === "waiting" && (
          <div className="text-sm text-slate-500 text-center py-2">
            Waiting for previous agents...
          </div>
        )}

        {/* Error state */}
        {status === "error" && (
          <div className="text-sm text-red-400 bg-red-500/10 rounded-md p-3">
            An error occurred during generation.
          </div>
        )}
      </div>

      {/* Actions */}
      {(onExpand || onViewRaw) && (
        <div className="flex items-center justify-end gap-2 px-4 py-2 border-t border-slate-700/50 bg-slate-900/30">
          {onExpand && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setIsExpanded(!isExpanded);
                onExpand();
              }}
              className="text-xs"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-3 h-3 mr-1" />
                  Collapse
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3 mr-1" />
                  Expand
                </>
              )}
            </Button>
          )}
          {onViewRaw && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onViewRaw}
              className="text-xs"
            >
              <Eye className="w-3 h-3 mr-1" />
              View Raw API
            </Button>
          )}
        </div>
      )}
    </motion.div>
  );
}

// ============================================================================
// LANE PROGRESS COMPARISON
// ============================================================================

interface LaneProgressComparisonProps {
  laneAAgents: Array<{
    role: AgentRole;
    status: AgentStatus;
    tokensGenerated: number;
    tokensEstimated: number;
    elapsedTime: number;
  }>;
  laneBAgents: Array<{
    role: AgentRole;
    status: AgentStatus;
    tokensGenerated: number;
    tokensEstimated: number;
    elapsedTime: number;
  }>;
}

export function LaneProgressComparison({ laneAAgents, laneBAgents }: LaneProgressComparisonProps) {
  const calculateLaneProgress = (agents: typeof laneAAgents) => {
    if (agents.length === 0) return 0;
    const completed = agents.filter(a => a.status === "complete").length;
    return Math.round((completed / agents.length) * 100);
  };

  const laneAProgress = calculateLaneProgress(laneAAgents);
  const laneBProgress = calculateLaneProgress(laneBAgents);

  const laneAComplete = laneAAgents.filter(a => a.status === "complete").length;
  const laneBComplete = laneBAgents.filter(a => a.status === "complete").length;

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Lane A */}
      <div className="rounded-lg border border-green-500/30 bg-green-500/5 p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-green-400">🟢 LANE A</span>
          <span className="text-xs text-slate-400">
            {laneAComplete} of {laneAAgents.length} agents
          </span>
        </div>
        
        <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden mb-3">
          <div 
            className="h-full bg-green-500 rounded-full transition-all"
            style={{ width: `${laneAProgress}%` }}
          />
        </div>

        <div className="space-y-2">
          {laneAAgents.map(agent => (
            <div key={agent.role} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span 
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: AGENT_COLORS[agent.role] }}
                />
                <span className="text-slate-300">{AGENT_LABELS[agent.role]}</span>
              </div>
              <span className={cn(
                agent.status === "complete" && "text-green-400",
                agent.status === "generating" && "text-cyan-400",
                agent.status === "waiting" && "text-slate-500"
              )}>
                {agent.status === "complete" && `✓ Done (${agent.elapsedTime.toFixed(0)}s)`}
                {agent.status === "generating" && `⚡ ${agent.tokensGenerated}/~${agent.tokensEstimated}`}
                {agent.status === "waiting" && "○ Waiting"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Lane B */}
      <div className="rounded-lg border border-purple-500/30 bg-purple-500/5 p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-purple-400">🟣 LANE B</span>
          <span className="text-xs text-slate-400">
            {laneBComplete} of {laneBAgents.length} agents
          </span>
        </div>
        
        <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden mb-3">
          <div 
            className="h-full bg-purple-500 rounded-full transition-all"
            style={{ width: `${laneBProgress}%` }}
          />
        </div>

        <div className="space-y-2">
          {laneBAgents.map(agent => (
            <div key={agent.role} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span 
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: AGENT_COLORS[agent.role] }}
                />
                <span className="text-slate-300">{AGENT_LABELS[agent.role]}</span>
              </div>
              <span className={cn(
                agent.status === "complete" && "text-green-400",
                agent.status === "generating" && "text-cyan-400",
                agent.status === "waiting" && "text-slate-500"
              )}>
                {agent.status === "complete" && `✓ Done (${agent.elapsedTime.toFixed(0)}s)`}
                {agent.status === "generating" && `⚡ ${agent.tokensGenerated}/~${agent.tokensEstimated}`}
                {agent.status === "waiting" && "○ Waiting"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

