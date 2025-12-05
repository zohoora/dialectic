"use client";

import { motion } from "framer-motion";
import { Layers, GitBranch, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

// ============================================================================
// TYPES
// ============================================================================

export type ConferenceVersion = "v1" | "v2.1" | "v3";

interface VersionToggleProps {
  version: ConferenceVersion;
  onVersionChange: (version: ConferenceVersion) => void;
  disabled?: boolean;
  showDescription?: boolean;
  size?: "sm" | "md" | "lg";
}

// ============================================================================
// DESCRIPTIONS
// ============================================================================

const VERSION_INFO: Record<ConferenceVersion, { 
  label: string; 
  shortLabel: string;
  description: string;
  icon: React.ElementType;
  color: string;
}> = {
  "v1": {
    label: "Standard",
    shortLabel: "v1",
    description: "Classic multi-round deliberation",
    icon: Layers,
    color: "slate",
  },
  "v2.1": {
    label: "Advanced",
    shortLabel: "v2.1",
    description: "Two-lane with Scout & cross-examination",
    icon: GitBranch,
    color: "cyan",
  },
  "v3": {
    label: "Adaptive",
    shortLabel: "v3",
    description: "Auto-selects optimal topology per query",
    icon: Zap,
    color: "violet",
  },
};

// ============================================================================
// VERSION TOGGLE (Three-way: v1, v2.1, v3)
// ============================================================================

export function VersionToggle({ 
  version, 
  onVersionChange, 
  disabled = false,
  showDescription = true,
  size = "md",
}: VersionToggleProps) {
  const versions: ConferenceVersion[] = ["v1", "v2.1", "v3"];
  const currentIndex = versions.indexOf(version);
  
  const getVersionStyle = (v: ConferenceVersion, isActive: boolean) => {
    if (!isActive) return "text-slate-500 hover:text-slate-400";
    switch (v) {
      case "v1": return "text-slate-200";
      case "v2.1": return "text-cyan-400";
      case "v3": return "text-violet-400";
    }
  };
  
  const getActiveStyle = (v: ConferenceVersion) => {
    switch (v) {
      case "v1": return "bg-slate-700 text-slate-200";
      case "v2.1": return "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30";
      case "v3": return "bg-violet-500/20 text-violet-400 border border-violet-500/30";
    }
  };
  
  return (
    <div className="flex flex-col items-center gap-2">
      {/* Three-way toggle */}
      <div className={cn(
        "inline-flex items-center rounded-lg p-1",
        "bg-slate-800 border border-slate-700"
      )}>
        {versions.map((v) => {
          const info = VERSION_INFO[v];
          const Icon = info.icon;
          const isActive = version === v;
          
          return (
            <button
              key={v}
              onClick={() => !disabled && onVersionChange(v)}
              disabled={disabled}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                isActive ? getActiveStyle(v) : "text-slate-500 hover:text-slate-400",
                disabled && "cursor-not-allowed"
              )}
            >
              <Icon className="w-3 h-3" />
              {info.shortLabel}
            </button>
          );
        })}
      </div>
      
      {/* Description */}
      {showDescription && (
        <p className={cn(
          "text-[11px] text-center max-w-[220px]",
          version === "v3" ? "text-violet-400/70" : 
          version === "v2.1" ? "text-cyan-400/70" : "text-slate-500"
        )}>
          {VERSION_INFO[version].description}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// COMPACT VERSION BADGE (for header)
// ============================================================================

interface VersionBadgeProps {
  version: ConferenceVersion;
  onClick?: () => void;
}

export function VersionBadge({ version, onClick }: VersionBadgeProps) {
  const info = VERSION_INFO[version];
  const Icon = info.icon;
  
  const getStyle = () => {
    switch (version) {
      case "v3": return "bg-violet-500/10 text-violet-400 border-violet-500/30 hover:bg-violet-500/20";
      case "v2.1": return "bg-cyan-500/10 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/20";
      default: return "bg-slate-700/50 text-slate-400 border-slate-600/50 hover:bg-slate-700";
    }
  };
  
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all",
        "border",
        getStyle(),
        onClick && "cursor-pointer"
      )}
    >
      <Icon className="w-3 h-3" />
      {version}
    </button>
  );
}

// ============================================================================
// INLINE VERSION TOGGLE (for embedded use)
// ============================================================================

interface InlineVersionToggleProps {
  version: ConferenceVersion;
  onVersionChange: (version: ConferenceVersion) => void;
  disabled?: boolean;
}

export function InlineVersionToggle({ 
  version, 
  onVersionChange, 
  disabled = false 
}: InlineVersionToggleProps) {
  const versions: ConferenceVersion[] = ["v1", "v2.1", "v3"];
  
  const getActiveStyle = (v: ConferenceVersion) => {
    switch (v) {
      case "v1": return "bg-slate-700 text-slate-200";
      case "v2.1": return "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30";
      case "v3": return "bg-violet-500/20 text-violet-400 border border-violet-500/30";
    }
  };
  
  return (
    <div className={cn(
      "inline-flex items-center rounded-lg p-1",
      "bg-slate-800 border border-slate-700"
    )}>
      {versions.map((v) => {
        const info = VERSION_INFO[v];
        const Icon = info.icon;
        const isActive = version === v;
        
        return (
          <button
            key={v}
            onClick={() => !disabled && onVersionChange(v)}
            disabled={disabled}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
              isActive ? getActiveStyle(v) : "text-slate-500 hover:text-slate-400",
              disabled && "cursor-not-allowed"
            )}
          >
            <Icon className="w-3 h-3" />
            {info.shortLabel}
          </button>
        );
      })}
    </div>
  );
}

