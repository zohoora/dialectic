"use client";

import { motion } from "framer-motion";
import { 
  Heart, 
  FlaskConical, 
  Cog, 
  AlertTriangle, 
  User, 
  Scale,
  Brain
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CircularProgress } from "@/components/ui/progress";
import type { AgentState } from "@/hooks/useConference";

const ROLE_CONFIG: Record<string, { 
  icon: React.ElementType; 
  color: string; 
  gradient: string;
  label: string;
}> = {
  advocate: {
    icon: Heart,
    color: "text-green-400",
    gradient: "from-green-500/20 to-transparent",
    label: "Advocate",
  },
  empiricist: {
    icon: FlaskConical,
    color: "text-blue-400",
    gradient: "from-blue-500/20 to-transparent",
    label: "Empiricist",
  },
  mechanist: {
    icon: Cog,
    color: "text-purple-400",
    gradient: "from-purple-500/20 to-transparent",
    label: "Mechanist",
  },
  skeptic: {
    icon: AlertTriangle,
    color: "text-red-400",
    gradient: "from-red-500/20 to-transparent",
    label: "Skeptic",
  },
  patient_voice: {
    icon: User,
    color: "text-yellow-400",
    gradient: "from-yellow-500/20 to-transparent",
    label: "Patient Voice",
  },
  arbitrator: {
    icon: Scale,
    color: "text-cyan-400",
    gradient: "from-cyan-500/20 to-transparent",
    label: "Arbitrator",
  },
};

interface AgentCardProps {
  agent: AgentState;
  expanded?: boolean;
  onToggleExpand?: () => void;
}

export function AgentCard({ agent, expanded = false, onToggleExpand }: AgentCardProps) {
  const config = ROLE_CONFIG[agent.role] || {
    icon: Brain,
    color: "text-slate-400",
    gradient: "from-slate-500/20 to-transparent",
    label: agent.role,
  };

  const Icon = config.icon;
  const isActive = agent.status === "thinking" || agent.status === "responding";
  const isComplete = agent.status === "complete";

  // Get glow color based on role
  const glowMap: Record<string, "cyan" | "purple" | "green" | "red" | "yellow" | "none"> = {
    advocate: "green",
    empiricist: "cyan",
    mechanist: "purple",
    skeptic: "red",
    patient_voice: "yellow",
    arbitrator: "cyan",
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card
        variant="glass"
        glow={isActive ? glowMap[agent.role] || "cyan" : "none"}
        className={cn(
          "relative overflow-hidden cursor-pointer transition-all duration-300",
          isActive && "ring-1 ring-white/20",
          expanded && "col-span-2"
        )}
        onClick={onToggleExpand}
      >
        {/* Gradient overlay */}
        <div
          className={cn(
            "absolute inset-0 bg-gradient-to-br opacity-50",
            config.gradient
          )}
        />

        {/* Content */}
        <div className="relative z-10">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "p-2 rounded-lg bg-white/5 border border-white/10",
                  isActive && "animate-pulse"
                )}
              >
                <Icon className={cn("w-5 h-5", config.color)} />
              </div>
              <div>
                <h3 className="font-medium text-slate-100">{config.label}</h3>
                <p className="text-xs text-slate-500 font-mono">
                  {agent.model.split("/").pop()}
                </p>
              </div>
            </div>

            {/* Status indicator */}
            <div className="flex items-center gap-2">
              {agent.status === "thinking" && (
                <div className="flex items-center gap-1.5">
                  <div className="typing-indicator flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-primary" />
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-primary" />
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-primary" />
                  </div>
                  <span className="text-xs text-slate-400">Thinking...</span>
                </div>
              )}

              {agent.status === "responding" && (
                <Badge variant="primary">Responding</Badge>
              )}

              {isComplete && agent.confidence !== null && (
                <CircularProgress
                  value={agent.confidence * 100}
                  size={40}
                  strokeWidth={3}
                  showValue={false}
                />
              )}
            </div>
          </div>

          {/* Confidence display */}
          {isComplete && agent.confidence !== null && (
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs text-slate-500">Confidence</span>
              <span className={cn("text-sm font-mono", config.color)}>
                {Math.round(agent.confidence * 100)}%
              </span>
              {agent.changed && (
                <Badge variant="warning" className="text-xs">
                  Position Changed
                </Badge>
              )}
            </div>
          )}

          {/* Content preview / full content */}
          {agent.content && (
            <div
              className={cn(
                "text-sm text-slate-300 leading-relaxed",
                !expanded && "line-clamp-3"
              )}
            >
              {agent.content}
            </div>
          )}

          {/* Expand hint */}
          {agent.content && !expanded && agent.content.length > 200 && (
            <p className="text-xs text-slate-500 mt-2">Click to expand</p>
          )}
        </div>
      </Card>
    </motion.div>
  );
}

// Compact version for grid display
export function AgentCardCompact({ agent }: { agent: AgentState }) {
  const config = ROLE_CONFIG[agent.role] || {
    icon: Brain,
    color: "text-slate-400",
    label: agent.role,
  };

  const Icon = config.icon;
  const isActive = agent.status === "thinking" || agent.status === "responding";

  return (
    <div
      className={cn(
        "flex items-center gap-3 p-3 rounded-lg border transition-all",
        "bg-void-200/30 border-white/5",
        isActive && "border-white/20 bg-void-200/50"
      )}
    >
      <div
        className={cn(
          "p-1.5 rounded-md bg-white/5",
          isActive && "animate-pulse"
        )}
      >
        <Icon className={cn("w-4 h-4", config.color)} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-200 truncate">
          {config.label}
        </p>
        <p className="text-xs text-slate-500">
          {agent.status === "thinking" && "Thinking..."}
          {agent.status === "responding" && "Responding..."}
          {agent.status === "complete" && agent.confidence !== null && (
            <span className={config.color}>{Math.round(agent.confidence * 100)}%</span>
          )}
          {agent.status === "idle" && "Waiting"}
        </p>
      </div>
      {isActive && (
        <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
      )}
    </div>
  );
}

