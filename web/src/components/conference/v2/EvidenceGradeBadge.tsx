"use client";

import { cn } from "@/lib/utils";

export type EvidenceGrade = 
  | "meta_analysis"
  | "rct_large"
  | "rct_small"
  | "observational"
  | "preprint"
  | "conflicting"
  | "case_report"
  | "expert_opinion";

interface EvidenceGradeBadgeProps {
  grade: EvidenceGrade;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const GRADE_CONFIG: Record<EvidenceGrade, {
  icon: string;
  label: string;
  shortLabel: string;
  color: string;
  bgColor: string;
  description: string;
}> = {
  meta_analysis: {
    icon: "🟣",
    label: "Meta-Analysis",
    shortLabel: "Meta",
    color: "var(--evidence-meta)",
    bgColor: "rgba(192, 132, 252, 0.15)",
    description: "Highest evidence quality",
  },
  rct_large: {
    icon: "🟢",
    label: "RCT (Large)",
    shortLabel: "RCT",
    color: "var(--evidence-rct)",
    bgColor: "rgba(34, 197, 94, 0.15)",
    description: "High quality randomized controlled trial",
  },
  rct_small: {
    icon: "🟢",
    label: "RCT (Small)",
    shortLabel: "RCT",
    color: "var(--evidence-rct)",
    bgColor: "rgba(34, 197, 94, 0.15)",
    description: "Small randomized controlled trial",
  },
  observational: {
    icon: "🟡",
    label: "Observational",
    shortLabel: "Obs",
    color: "var(--evidence-observational)",
    bgColor: "rgba(250, 204, 21, 0.15)",
    description: "Observational study",
  },
  preprint: {
    icon: "🟠",
    label: "Preprint",
    shortLabel: "Pre",
    color: "var(--evidence-preprint)",
    bgColor: "rgba(251, 146, 60, 0.15)",
    description: "Not peer-reviewed",
  },
  conflicting: {
    icon: "🔴",
    label: "Conflicting",
    shortLabel: "Conf",
    color: "var(--evidence-conflict)",
    bgColor: "rgba(239, 68, 68, 0.15)",
    description: "Conflicting evidence",
  },
  case_report: {
    icon: "🟡",
    label: "Case Report",
    shortLabel: "Case",
    color: "var(--evidence-observational)",
    bgColor: "rgba(250, 204, 21, 0.15)",
    description: "Individual case report",
  },
  expert_opinion: {
    icon: "⚪",
    label: "Expert Opinion",
    shortLabel: "Expert",
    color: "var(--text-muted)",
    bgColor: "rgba(100, 116, 139, 0.15)",
    description: "Expert consensus without research backing",
  },
};

export function EvidenceGradeBadge({ 
  grade, 
  showLabel = true, 
  size = "md",
  className 
}: EvidenceGradeBadgeProps) {
  const config = GRADE_CONFIG[grade] || GRADE_CONFIG.expert_opinion;
  
  const sizeClasses = {
    sm: "text-xs px-1.5 py-0.5",
    md: "text-sm px-2 py-1",
    lg: "text-base px-3 py-1.5",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-medium",
        sizeClasses[size],
        className
      )}
      style={{ 
        backgroundColor: config.bgColor,
        color: config.color,
      }}
      title={config.description}
      role="img"
      aria-label={`${config.label}: ${config.description}`}
    >
      <span>{config.icon}</span>
      {showLabel && (
        <span>{size === "sm" ? config.shortLabel : config.label}</span>
      )}
    </span>
  );
}

// Legend component for reference
export function EvidenceGradeLegend() {
  return (
    <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
      <h4 className="text-sm font-medium text-slate-300 mb-3">Evidence Grade Guide</h4>
      <div className="space-y-2">
        {(Object.entries(GRADE_CONFIG) as [EvidenceGrade, typeof GRADE_CONFIG[EvidenceGrade]][]).map(([grade, config]) => (
          <div key={grade} className="flex items-center gap-2">
            <EvidenceGradeBadge grade={grade} size="sm" />
            <span className="text-xs text-slate-400">{config.description}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

