"use client";

import { motion } from "framer-motion";
import { Layers, GitBranch } from "lucide-react";
import { cn } from "@/lib/utils";

// ============================================================================
// TYPES
// ============================================================================

export type ConferenceVersion = "v1" | "v2.1";

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
}> = {
  "v1": {
    label: "Standard",
    shortLabel: "v1",
    description: "Classic multi-round deliberation",
    icon: Layers,
  },
  "v2.1": {
    label: "Advanced",
    shortLabel: "v2.1",
    description: "Two-lane with Scout & cross-examination",
    icon: GitBranch,
  },
};

// ============================================================================
// VERSION TOGGLE
// ============================================================================

export function VersionToggle({ 
  version, 
  onVersionChange, 
  disabled = false,
  showDescription = true,
  size = "md",
}: VersionToggleProps) {
  const isV21 = version === "v2.1";
  
  const sizeConfig = {
    sm: { 
      width: "w-16", 
      height: "h-7", 
      thumb: "w-7 h-5",
      text: "text-[10px]",
      icon: "w-3 h-3",
    },
    md: { 
      width: "w-20", 
      height: "h-8", 
      thumb: "w-9 h-6",
      text: "text-xs",
      icon: "w-3.5 h-3.5",
    },
    lg: { 
      width: "w-24", 
      height: "h-10", 
      thumb: "w-11 h-8",
      text: "text-sm",
      icon: "w-4 h-4",
    },
  };
  
  const config = sizeConfig[size];
  
  return (
    <div className="flex flex-col items-center gap-2">
      {/* Labels */}
      {showDescription && (
        <div className="flex items-center justify-between w-full max-w-[180px] px-1">
          <span className={cn(
            "text-xs font-medium transition-colors",
            !isV21 ? "text-slate-200" : "text-slate-500"
          )}>
            {VERSION_INFO["v1"].label}
          </span>
          <span className={cn(
            "text-xs font-medium transition-colors",
            isV21 ? "text-cyan-400" : "text-slate-500"
          )}>
            {VERSION_INFO["v2.1"].label}
          </span>
        </div>
      )}
      
      {/* Toggle Switch */}
      <button
        role="switch"
        aria-checked={isV21}
        aria-label="Toggle between standard and advanced conference modes"
        onClick={() => !disabled && onVersionChange(isV21 ? "v1" : "v2.1")}
        disabled={disabled}
        className={cn(
          "relative rounded-full transition-all duration-200",
          config.width,
          config.height,
          isV21 
            ? "bg-cyan-500/15 border border-cyan-500/50 shadow-[0_0_12px_rgba(34,211,238,0.2)]" 
            : "bg-slate-700 border border-slate-600",
          disabled && "opacity-50 cursor-not-allowed",
          !disabled && "cursor-pointer hover:border-opacity-75"
        )}
      >
        {/* Thumb */}
        <motion.div
          className={cn(
            "absolute top-1 flex items-center justify-center rounded-full font-semibold",
            config.thumb,
            config.text,
            isV21 
              ? "bg-cyan-400 text-slate-900" 
              : "bg-slate-500 text-slate-200"
          )}
          initial={false}
          animate={{ 
            left: isV21 ? `calc(100% - ${parseInt(config.thumb.split(" ")[0].replace("w-", "")) * 4}px - 4px)` : "4px" 
          }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        >
          {isV21 ? VERSION_INFO["v2.1"].shortLabel : VERSION_INFO["v1"].shortLabel}
        </motion.div>
      </button>
      
      {/* Description */}
      {showDescription && (
        <p className="text-[11px] text-slate-500 text-center max-w-[200px]">
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
  const isV21 = version === "v2.1";
  const info = VERSION_INFO[version];
  const Icon = info.icon;
  
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all",
        "border",
        isV21 
          ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/20" 
          : "bg-slate-700/50 text-slate-400 border-slate-600/50 hover:bg-slate-700",
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
  const isV21 = version === "v2.1";
  
  return (
    <div className={cn(
      "inline-flex items-center rounded-lg p-1",
      "bg-slate-800 border border-slate-700"
    )}>
      <button
        onClick={() => !disabled && onVersionChange("v1")}
        disabled={disabled}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
          !isV21 
            ? "bg-slate-700 text-slate-200" 
            : "text-slate-500 hover:text-slate-400",
          disabled && "cursor-not-allowed"
        )}
      >
        <Layers className="w-3 h-3" />
        v1
      </button>
      
      <button
        onClick={() => !disabled && onVersionChange("v2.1")}
        disabled={disabled}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
          isV21 
            ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30" 
            : "text-slate-500 hover:text-slate-400",
          disabled && "cursor-not-allowed"
        )}
      >
        <GitBranch className="w-3 h-3" />
        v2.1
      </button>
    </div>
  );
}

