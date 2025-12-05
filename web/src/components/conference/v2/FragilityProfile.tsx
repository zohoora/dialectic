"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Shield, 
  Check, 
  X, 
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// ============================================================================
// TYPES
// ============================================================================

export type FragilityResult = "holds" | "modified" | "changes";

export interface FragilityEntry {
  perturbation: string;
  description: string;
  result: FragilityResult;
  modification?: string;
  alternativeRecommendation?: string;
}

interface FragilityProfileProps {
  entries: FragilityEntry[];
  collapsed?: boolean;
  onToggle?: () => void;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const RESULT_CONFIG: Record<FragilityResult, {
  icon: React.ElementType;
  label: string;
  color: string;
  bgColor: string;
}> = {
  holds: {
    icon: Check,
    label: "Holds",
    color: "text-green-400",
    bgColor: "bg-green-500/10",
  },
  modified: {
    icon: AlertTriangle,
    label: "Modified",
    color: "text-amber-400",
    bgColor: "bg-amber-500/10",
  },
  changes: {
    icon: X,
    label: "Changes",
    color: "text-red-400",
    bgColor: "bg-red-500/10",
  },
};

// ============================================================================
// FRAGILITY ENTRY ROW
// ============================================================================

interface FragilityEntryRowProps {
  entry: FragilityEntry;
  index: number;
}

function FragilityEntryRow({ entry, index }: FragilityEntryRowProps) {
  const [expanded, setExpanded] = useState(false);
  const config = RESULT_CONFIG[entry.result];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className={cn(
        "rounded-lg border overflow-hidden",
        entry.result === "holds" && "border-green-500/30",
        entry.result === "modified" && "border-amber-500/30",
        entry.result === "changes" && "border-red-500/30"
      )}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "w-full flex items-center gap-3 px-4 py-3 text-left transition-colors",
          config.bgColor,
          "hover:bg-opacity-70"
        )}
      >
        <Icon className={cn("w-4 h-4", config.color)} />
        
        <span className="flex-1 text-sm text-slate-200">
          {entry.perturbation}
        </span>
        
        <Badge className={cn(
          "text-xs",
          entry.result === "holds" && "bg-green-500/20 text-green-400",
          entry.result === "modified" && "bg-amber-500/20 text-amber-400",
          entry.result === "changes" && "bg-red-500/20 text-red-400"
        )}>
          {entry.result === "changes" ? "CHANGES" : entry.result === "modified" ? "MODIFIED" : "HOLDS"}
        </Badge>
        
        {(entry.modification || entry.alternativeRecommendation) && (
          expanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )
        )}
      </button>
      
      <AnimatePresence>
        {expanded && (entry.modification || entry.alternativeRecommendation) && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-4 py-3 border-t border-slate-700/50 bg-slate-800/30"
          >
            {entry.description && (
              <p className="text-xs text-slate-400 mb-2">{entry.description}</p>
            )}
            {entry.modification && (
              <div className="mb-2">
                <span className="text-xs text-amber-400 font-medium">Modification: </span>
                <span className="text-sm text-slate-300">{entry.modification}</span>
              </div>
            )}
            {entry.alternativeRecommendation && (
              <div>
                <span className="text-xs text-red-400 font-medium">Alternative: </span>
                <span className="text-sm text-slate-300">{entry.alternativeRecommendation}</span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ============================================================================
// SURVIVAL RATE BAR
// ============================================================================

interface SurvivalRateBarProps {
  survived: number;
  total: number;
}

function SurvivalRateBar({ survived, total }: SurvivalRateBarProps) {
  const percentage = total > 0 ? Math.round((survived / total) * 100) : 0;
  
  const getColor = () => {
    if (percentage >= 80) return "bg-green-500";
    if (percentage >= 60) return "bg-amber-500";
    return "bg-red-500";
  };
  
  const getTextColor = () => {
    if (percentage >= 80) return "text-green-400";
    if (percentage >= 60) return "text-amber-400";
    return "text-red-400";
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-400">Survival Rate</span>
        <span className={cn("font-semibold", getTextColor())}>
          {percentage}% ({survived}/{total} perturbations)
        </span>
      </div>
      <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
        <motion.div
          className={cn("h-full rounded-full", getColor())}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

// ============================================================================
// FRAGILITY PROFILE
// ============================================================================

export function FragilityProfile({ entries, collapsed = false, onToggle }: FragilityProfileProps) {
  const survived = entries.filter(e => e.result === "holds" || e.result === "modified").length;
  const changed = entries.filter(e => e.result === "changes").length;
  const modified = entries.filter(e => e.result === "modified").length;

  return (
    <Card className="bg-slate-800/30 border-slate-700/50">
      <CardHeader
        className={cn(
          "py-4 px-4 border-b border-slate-700/50",
          onToggle && "cursor-pointer hover:bg-slate-800/50 transition-colors"
        )}
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/20">
              <Shield className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <h3 className="font-medium text-slate-200">Fragility Profile</h3>
              <p className="text-xs text-slate-400">
                How robust is this recommendation to patient changes?
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {changed > 0 && (
              <Badge className="bg-red-500/20 text-red-400">
                {changed} fragile
              </Badge>
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
      </CardHeader>
      
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <CardContent className="pt-4 space-y-4">
              {/* Survival Rate */}
              <SurvivalRateBar survived={survived} total={entries.length} />
              
              {/* Entries */}
              <div className="space-y-2">
                <h4 className="text-xs text-slate-500 uppercase tracking-wider">
                  Tested Perturbations
                </h4>
                <div className="space-y-2">
                  {entries.map((entry, idx) => (
                    <FragilityEntryRow key={idx} entry={entry} index={idx} />
                  ))}
                </div>
              </div>
              
              {/* Warning if fragile conditions */}
              {changed > 0 && (
                <div className="rounded-md bg-red-500/10 border border-red-500/30 p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <span className="text-sm font-medium text-red-400">
                        ⚠️ {changed} FRAGILE CONDITION{changed > 1 ? "S" : ""}:
                      </span>
                      <p className="text-sm text-slate-300 mt-1">
                        {entries.filter(e => e.result === "changes").map(e => e.perturbation).join(", ")}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// ============================================================================
// DEMO DATA
// ============================================================================

export const DEMO_FRAGILITY_ENTRIES: FragilityEntry[] = [
  {
    perturbation: "Renal impairment",
    description: "What if the patient has CKD stage 4-5?",
    result: "holds",
    modification: undefined,
  },
  {
    perturbation: "Hepatic impairment",
    description: "What if the patient has liver disease?",
    result: "holds",
  },
  {
    perturbation: "Anticoagulation",
    description: "What if the patient is on blood thinners?",
    result: "modified",
    modification: "Adjust timing of procedure, coordinate with anticoagulation management",
  },
  {
    perturbation: "Pregnancy",
    description: "What if the patient is pregnant?",
    result: "changes",
    alternativeRecommendation: "Defer neuromodulation until postpartum. Consider conservative measures only.",
  },
  {
    perturbation: "Elderly (>75)",
    description: "What if the patient is over 75 years old?",
    result: "holds",
  },
  {
    perturbation: "Cost constraint",
    description: "What if insurance doesn't cover the treatment?",
    result: "modified",
    modification: "Alternative pathway: trial SCS before DRG if cost is prohibitive",
  },
  {
    perturbation: "Active substance use",
    description: "What if the patient has active substance use disorder?",
    result: "changes",
    alternativeRecommendation: "Address substance use first. Implantable devices contraindicated in active SUD.",
  },
  {
    perturbation: "Polypharmacy",
    description: "What if the patient is on >10 medications?",
    result: "holds",
    modification: "Monitor for drug interactions, no fundamental change to recommendation",
  },
];

