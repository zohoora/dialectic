"use client";

import { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Lane = "A" | "B";

interface LaneContainerProps {
  lane: Lane;
  children: ReactNode;
  className?: string;
  isStreaming?: boolean;
}

const LANE_CONFIG = {
  A: {
    icon: "🟢",
    title: "CLINICAL CONSENSUS",
    subtitle: "Evidence-based, actionable recommendations",
    badge: "SAFE TO ACT ON",
    badgeClass: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  },
  B: {
    icon: "🟣",
    title: "EXPLORATION",
    subtitle: "Theoretical approaches and hypotheses",
    badge: "REQUIRES VALIDATION",
    badgeClass: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  },
};

export function LaneContainer({
  lane,
  children,
  className,
  isStreaming = false,
}: LaneContainerProps) {
  const config = LANE_CONFIG[lane];
  const laneClass = lane === "A" ? "lane-a" : "lane-b";

  return (
    <div 
      className={cn(
        laneClass,
        "min-h-[300px] p-5",
        isStreaming && "streaming",
        className
      )}
      style={isStreaming ? { 
        "--glow-color": lane === "A" 
          ? "var(--lane-a-primary)" 
          : "var(--lane-b-primary)" 
      } as React.CSSProperties : undefined}
    >
      {/* Lane Header */}
      <div className="lane-header pb-4 mb-4 -mx-5 px-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{config.icon}</span>
            <div>
              <h2 
                className="text-sm font-semibold uppercase tracking-widest"
                style={{ 
                  color: lane === "A" 
                    ? "var(--lane-a-primary)" 
                    : "var(--lane-b-primary)" 
                }}
              >
                {config.title}
              </h2>
              <p className="text-xs text-slate-400">{config.subtitle}</p>
            </div>
          </div>
          <Badge className={cn("border text-xs", config.badgeClass)}>
            {config.badge}
          </Badge>
        </div>
      </div>
      
      {/* Lane Content */}
      <div className="space-y-4">
        {children}
      </div>
    </div>
  );
}

// Two-lane layout wrapper
interface TwoLaneLayoutProps {
  laneA: ReactNode;
  laneB: ReactNode;
  className?: string;
}

export function TwoLaneLayout({ laneA, laneB, className }: TwoLaneLayoutProps) {
  return (
    <div className={cn("grid grid-cols-1 lg:grid-cols-2 gap-6", className)}>
      <LaneContainer lane="A">
        {laneA}
      </LaneContainer>
      <LaneContainer lane="B">
        {laneB}
      </LaneContainer>
    </div>
  );
}

