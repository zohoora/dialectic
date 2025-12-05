"use client";

import { cn } from "@/lib/utils";

type ConfidenceLevel = "HIGH" | "MODERATE" | "LOW" | "SPECULATIVE";

interface ConfidenceMeterProps {
  percentage: number;
  level?: ConfidenceLevel;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

function getConfidenceLevel(percentage: number): ConfidenceLevel {
  if (percentage >= 80) return "HIGH";
  if (percentage >= 50) return "MODERATE";
  if (percentage >= 25) return "LOW";
  return "SPECULATIVE";
}

const LEVEL_CONFIG: Record<ConfidenceLevel, {
  color: string;
  bgColor: string;
  label: string;
}> = {
  HIGH: {
    color: "var(--confidence-high)",
    bgColor: "rgba(34, 197, 94, 0.2)",
    label: "High",
  },
  MODERATE: {
    color: "var(--confidence-moderate)",
    bgColor: "rgba(250, 204, 21, 0.2)",
    label: "Moderate",
  },
  LOW: {
    color: "var(--confidence-low)",
    bgColor: "rgba(251, 146, 60, 0.2)",
    label: "Low",
  },
  SPECULATIVE: {
    color: "var(--confidence-speculative)",
    bgColor: "rgba(168, 85, 247, 0.2)",
    label: "Speculative",
  },
};

export function ConfidenceMeter({
  percentage,
  level,
  showLabel = true,
  size = "md",
  className,
}: ConfidenceMeterProps) {
  const actualLevel = level || getConfidenceLevel(percentage);
  const config = LEVEL_CONFIG[actualLevel];
  
  const sizeClasses = {
    sm: { bar: "h-1", text: "text-xs" },
    md: { bar: "h-1.5", text: "text-sm" },
    lg: { bar: "h-2", text: "text-base" },
  };

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Progress Bar */}
      <div className={cn(
        "flex-1 bg-slate-700 rounded-full overflow-hidden",
        sizeClasses[size].bar
      )}>
        <div 
          className="h-full rounded-full transition-all duration-500"
          style={{ 
            width: `${Math.min(percentage, 100)}%`,
            backgroundColor: config.color,
          }}
        />
      </div>
      
      {/* Label */}
      {showLabel && (
        <span 
          className={cn("font-medium", sizeClasses[size].text)}
          style={{ color: config.color }}
        >
          {config.label} ({Math.round(percentage)}%)
        </span>
      )}
    </div>
  );
}

// Simple badge version
export function ConfidenceBadge({
  percentage,
  className,
}: {
  percentage: number;
  className?: string;
}) {
  const level = getConfidenceLevel(percentage);
  const config = LEVEL_CONFIG[level];

  return (
    <span
      className={cn(
        "px-2 py-1 rounded-full text-xs font-medium",
        className
      )}
      style={{
        backgroundColor: config.bgColor,
        color: config.color,
      }}
    >
      {Math.round(percentage)}% {config.label}
    </span>
  );
}

