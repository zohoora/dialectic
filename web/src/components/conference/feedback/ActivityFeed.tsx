"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Activity, 
  ChevronDown, 
  ChevronUp, 
  Zap, 
  Search, 
  MessageSquare,
  CheckCircle2,
  XCircle,
  Clock,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ============================================================================
// TYPES
// ============================================================================

export type ActivityEventType = 
  | "conference_start"
  | "routing"
  | "routing_complete"
  | "scout_start"
  | "scout_complete"
  | "agent_start"
  | "agent_progress"
  | "agent_complete"
  | "agent_error"
  | "cross_exam_start"
  | "cross_exam_complete"
  | "synthesis_start"
  | "synthesis_complete"
  | "fragility_start"
  | "fragility_test"
  | "fragility_complete"
  | "conference_complete"
  | "conference_error";

export interface ActivityEvent {
  id: string;
  timestamp: Date;
  type: ActivityEventType;
  phase: string;
  status: "pending" | "running" | "complete" | "error";
  details: {
    agentRole?: string;
    tokensGenerated?: number;
    tokensEstimated?: number;
    message?: string;
    latency?: number;
    mode?: string;
    paperCount?: number;
    perturbation?: string;
    result?: "holds" | "changes" | "modified";
  };
}

// ============================================================================
// ACTIVITY EVENT ROW
// ============================================================================

interface ActivityEventRowProps {
  event: ActivityEvent;
  isLatest?: boolean;
}

export function ActivityEventRow({ event, isLatest }: ActivityEventRowProps) {
  const timeStr = event.timestamp.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });

  const getIcon = () => {
    switch (event.type) {
      case "conference_start":
        return <Activity className="w-3.5 h-3.5 text-cyan-400" />;
      case "routing":
      case "routing_complete":
        return <Zap className="w-3.5 h-3.5 text-cyan-400" />;
      case "scout_start":
      case "scout_complete":
        return <Search className="w-3.5 h-3.5 text-lime-400" />;
      case "agent_start":
      case "agent_progress":
        return <MessageSquare className="w-3.5 h-3.5 text-blue-400" />;
      case "agent_complete":
        return <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />;
      case "agent_error":
        return <XCircle className="w-3.5 h-3.5 text-red-400" />;
      case "synthesis_start":
      case "synthesis_complete":
        return <FileText className="w-3.5 h-3.5 text-cyan-400" />;
      case "fragility_start":
      case "fragility_test":
      case "fragility_complete":
        return <Activity className="w-3.5 h-3.5 text-amber-400" />;
      case "conference_complete":
        return <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />;
      case "conference_error":
        return <XCircle className="w-3.5 h-3.5 text-red-400" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const getStatusIndicator = () => {
    switch (event.status) {
      case "running":
        return <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />;
      case "complete":
        return <span className="w-2 h-2 rounded-full bg-green-400" />;
      case "error":
        return <span className="w-2 h-2 rounded-full bg-red-400" />;
      default:
        return <span className="w-2 h-2 rounded-full bg-slate-500" />;
    }
  };

  const getMessage = () => {
    const { details } = event;
    switch (event.type) {
      case "conference_start":
        return "Conference started";
      case "routing":
        return "Analyzing query complexity...";
      case "routing_complete":
        return `Routing complete → ${details.mode || "COMPLEX_DILEMMA"}`;
      case "scout_start":
        return "Scout searching literature...";
      case "scout_complete":
        return `Scout complete — ${details.paperCount || 0} papers found`;
      case "agent_start":
        return `${details.agentRole} generating...`;
      case "agent_progress":
        return `${details.agentRole} — ${details.tokensGenerated || 0}/${details.tokensEstimated || "~"} tokens`;
      case "agent_complete":
        return `${details.agentRole} complete${details.latency ? ` (${(details.latency / 1000).toFixed(1)}s)` : ""}`;
      case "agent_error":
        return `${details.agentRole} error: ${details.message}`;
      case "cross_exam_start":
        return "Cross-examination starting...";
      case "cross_exam_complete":
        return "Cross-examination complete";
      case "synthesis_start":
        return "Arbitrator synthesizing...";
      case "synthesis_complete":
        return `Synthesis complete${details.latency ? ` (${(details.latency / 1000).toFixed(1)}s)` : ""}`;
      case "fragility_start":
        return "Starting fragility testing...";
      case "fragility_test":
        return `Testing: ${details.perturbation} → ${details.result?.toUpperCase() || "..."}`;
      case "fragility_complete":
        return "Fragility testing complete";
      case "conference_complete":
        return "✓ Conference complete";
      case "conference_error":
        return `Error: ${details.message}`;
      default:
        return details.message || event.phase;
    }
  };

  return (
    <motion.div
      initial={isLatest ? { opacity: 0, x: -10 } : false}
      animate={{ opacity: 1, x: 0 }}
      className={cn(
        "flex items-start gap-3 py-2 px-3 rounded-lg",
        isLatest && "bg-slate-800/50",
        event.status === "error" && "bg-red-500/5"
      )}
    >
      <span className="text-xs text-slate-500 font-mono whitespace-nowrap pt-0.5">
        {timeStr}
      </span>
      
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {getIcon()}
        {getStatusIndicator()}
        <span className={cn(
          "text-sm truncate",
          event.status === "error" ? "text-red-400" : "text-slate-300"
        )}>
          {getMessage()}
        </span>
      </div>
    </motion.div>
  );
}

// ============================================================================
// ACTIVITY FEED
// ============================================================================

interface ActivityFeedProps {
  events: ActivityEvent[];
  maxHeight?: number;
  collapsed?: boolean;
  onToggle?: () => void;
}

export function ActivityFeed({ 
  events, 
  maxHeight = 300,
  collapsed = false,
  onToggle,
}: ActivityFeedProps) {
  const feedRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const latestEventId = events.length > 0 ? events[events.length - 1].id : null;

  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 overflow-hidden">
      {/* Header */}
      <div 
        className={cn(
          "flex items-center justify-between px-4 py-3 border-b border-slate-700/50",
          onToggle && "cursor-pointer hover:bg-slate-800/50"
        )}
        onClick={onToggle}
      >
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-medium text-slate-200">ACTIVITY FEED</span>
          {events.length > 0 && (
            <span className="text-xs text-slate-500">
              ({events.length} events)
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-3">
          {!collapsed && (
            <label className="flex items-center gap-2 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="w-3 h-3 rounded bg-slate-700 border-slate-600"
                onClick={(e) => e.stopPropagation()}
              />
              Auto-scroll
            </label>
          )}
          {onToggle && (
            collapsed ? (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            )
          )}
        </div>
      </div>

      {/* Events */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div 
              ref={feedRef}
              className="overflow-y-auto p-2 space-y-1"
              style={{ maxHeight }}
            >
              {events.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-sm">
                  No activity yet. Start a conference to see events.
                </div>
              ) : (
                events.map((event) => (
                  <ActivityEventRow 
                    key={event.id} 
                    event={event} 
                    isLatest={event.id === latestEventId}
                  />
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ============================================================================
// UTILITY: Create Event Helper
// ============================================================================

let eventCounter = 0;

export function createActivityEvent(
  type: ActivityEventType,
  phase: string,
  status: ActivityEvent["status"],
  details: ActivityEvent["details"] = {}
): ActivityEvent {
  return {
    id: `event-${++eventCounter}-${Date.now()}`,
    timestamp: new Date(),
    type,
    phase,
    status,
    details,
  };
}

