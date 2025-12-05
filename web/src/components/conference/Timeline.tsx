"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface TimelineEvent {
  id: string;
  label: string;
  status: "pending" | "active" | "complete";
  detail?: string;
}

interface TimelineProps {
  events: TimelineEvent[];
  currentRound: number;
  totalRounds: number;
}

export function Timeline({ events, currentRound, totalRounds }: TimelineProps) {
  return (
    <div className="relative">
      {/* Progress line */}
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-void-300" />

      {/* Events */}
      <div className="space-y-4">
        {events.map((event, index) => (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="relative flex items-start gap-4 pl-0"
          >
            {/* Icon */}
            <div
              className={cn(
                "relative z-10 flex items-center justify-center w-8 h-8 rounded-full border-2 transition-all",
                event.status === "complete" &&
                  "bg-green-500/20 border-green-500 text-green-400",
                event.status === "active" &&
                  "bg-accent-primary/20 border-accent-primary text-accent-primary animate-pulse",
                event.status === "pending" &&
                  "bg-void-200 border-white/10 text-slate-500"
              )}
            >
              {event.status === "complete" && <CheckCircle2 className="w-4 h-4" />}
              {event.status === "active" && <Loader2 className="w-4 h-4 animate-spin" />}
              {event.status === "pending" && <Circle className="w-4 h-4" />}
            </div>

            {/* Content */}
            <div className="flex-1 pt-1">
              <p
                className={cn(
                  "text-sm font-medium",
                  event.status === "active" && "text-accent-primary",
                  event.status === "complete" && "text-slate-200",
                  event.status === "pending" && "text-slate-500"
                )}
              >
                {event.label}
              </p>
              {event.detail && (
                <p className="text-xs text-slate-500 mt-0.5">{event.detail}</p>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Round indicator */}
      {totalRounds > 0 && (
        <div className="mt-6 pt-4 border-t border-white/5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500">Round Progress</span>
            <span className="text-accent-primary font-mono">
              {currentRound}/{totalRounds}
            </span>
          </div>
          <div className="mt-2 flex gap-1">
            {Array.from({ length: totalRounds }).map((_, i) => (
              <div
                key={i}
                className={cn(
                  "flex-1 h-1.5 rounded-full transition-all",
                  i < currentRound
                    ? "bg-accent-primary"
                    : i === currentRound
                    ? "bg-accent-primary/50 animate-pulse"
                    : "bg-void-300"
                )}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Horizontal mini timeline
export function MiniTimeline({
  currentRound,
  totalRounds,
  phase,
}: {
  currentRound: number;
  totalRounds: number;
  phase: string;
}) {
  // Don't show rounds if totalRounds is 0 (v2.1 mode)
  const showRounds = totalRounds > 0;
  
  return (
    <div className="flex items-center gap-4">
      {/* Phase badge */}
      <div className="px-3 py-1 rounded-full bg-accent-primary/10 border border-accent-primary/30">
        <span className="text-xs font-medium text-accent-primary">{phase || "Processing"}</span>
      </div>

      {/* Round dots - only show if there are rounds */}
      {showRounds && (
        <>
          <div className="flex items-center gap-2">
            {Array.from({ length: totalRounds }).map((_, i) => (
              <div
                key={i}
                className={cn(
                  "w-2.5 h-2.5 rounded-full transition-all",
                  i < currentRound
                    ? "bg-green-500"
                    : i === currentRound
                    ? "bg-accent-primary animate-pulse ring-2 ring-accent-primary/30"
                    : "bg-void-300"
                )}
              />
            ))}
          </div>

          {/* Round label */}
          <span className="text-sm text-slate-400">
            Round <span className="text-slate-200 font-mono">{currentRound}</span> of{" "}
            <span className="text-slate-200 font-mono">{totalRounds}</span>
          </span>
        </>
      )}
    </div>
  );
}

