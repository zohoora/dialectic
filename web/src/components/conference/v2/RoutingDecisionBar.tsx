"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Route, 
  Zap, 
  ChevronDown, 
  Search, 
  Users,
  AlertTriangle,
  FileText,
  Microscope,
  HelpCircle
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type ConferenceMode = 
  | "STANDARD_CARE" 
  | "COMPLEX_DILEMMA" 
  | "NOVEL_RESEARCH" 
  | "DIAGNOSTIC_PUZZLE";

interface RoutingDecisionBarProps {
  mode: ConferenceMode;
  agentCount: number;
  scoutActive: boolean;
  riskProfile: number;
  rationale?: string;
  complexitySignals?: string[];
  activeAgents?: string[];
  isRouting?: boolean;
}

const MODE_CONFIG: Record<ConferenceMode, {
  label: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  description: string;
}> = {
  STANDARD_CARE: {
    label: "STANDARD",
    icon: <FileText className="w-4 h-4" />,
    color: "#64748b",
    bgColor: "rgba(100, 116, 139, 0.2)",
    description: "Guideline check",
  },
  COMPLEX_DILEMMA: {
    label: "COMPLEX",
    icon: <AlertTriangle className="w-4 h-4" />,
    color: "#f59e0b",
    bgColor: "rgba(245, 158, 11, 0.2)",
    description: "Multi-factor decision",
  },
  NOVEL_RESEARCH: {
    label: "NOVEL",
    icon: <Microscope className="w-4 h-4" />,
    color: "#a855f7",
    bgColor: "rgba(168, 85, 247, 0.2)",
    description: "Experimental territory",
  },
  DIAGNOSTIC_PUZZLE: {
    label: "DIAGNOSTIC",
    icon: <HelpCircle className="w-4 h-4" />,
    color: "#3b82f6",
    bgColor: "rgba(59, 130, 246, 0.2)",
    description: "Unclear diagnosis",
  },
};

export function RoutingDecisionBar({
  mode,
  agentCount,
  scoutActive,
  riskProfile,
  rationale,
  complexitySignals = [],
  activeAgents = [],
  isRouting = false,
}: RoutingDecisionBarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const config = MODE_CONFIG[mode] || MODE_CONFIG.COMPLEX_DILEMMA;

  // Group agents by lane
  const laneAAgents = activeAgents.filter(a => 
    ["empiricist", "skeptic", "pragmatist", "patient_voice"].includes(a.toLowerCase())
  );
  const laneBAgents = activeAgents.filter(a => 
    ["mechanist", "speculator"].includes(a.toLowerCase())
  );

  return (
    <div 
      className={cn(
        "border-b transition-all duration-200",
        isRouting 
          ? "routing-bar routing border-cyan-500/50" 
          : "routing-bar border-slate-700/50"
      )}
    >
      {/* Compact Bar */}
      <button
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-4">
          {/* Router Icon */}
          <div className={cn(
            "p-2 rounded-lg",
            isRouting ? "bg-cyan-500/20" : "bg-slate-800/50"
          )}>
            {isRouting ? (
              <Route className="w-4 h-4 text-cyan-400 animate-pulse" />
            ) : complexitySignals.length > 0 ? (
              <Zap className="w-4 h-4 text-amber-400" />
            ) : (
              <Route className="w-4 h-4 text-slate-400" />
            )}
          </div>
          
          {/* Status Text */}
          {isRouting ? (
            <span className="text-sm text-cyan-400">Analyzing query complexity...</span>
          ) : (
            <div className="flex items-center gap-3">
              {/* Mode Badge */}
              <Badge 
                style={{ 
                  backgroundColor: config.bgColor,
                  color: config.color,
                  borderColor: config.color,
                }}
                className="border font-medium"
              >
                {config.icon}
                <span className="ml-1">{config.label}</span>
              </Badge>
              
              {/* Agent Count */}
              <div className="flex items-center gap-1 text-sm text-slate-400">
                <Users className="w-3.5 h-3.5" />
                <span>{agentCount} agents</span>
              </div>
              
              {/* Scout Indicator */}
              <div className={cn(
                "flex items-center gap-1 text-sm",
                scoutActive ? "text-lime-400" : "text-slate-500"
              )}>
                <Search className="w-3.5 h-3.5" />
                <span>Scout {scoutActive ? "✓" : "✗"}</span>
              </div>
              
              {/* Risk Profile */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Risk:</span>
                <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-full"
                    style={{ width: `${riskProfile * 100}%` }}
                  />
                </div>
                <span className="text-xs text-slate-400">{riskProfile.toFixed(1)}</span>
              </div>
            </div>
          )}
        </div>
        
        {!isRouting && (
          <ChevronDown className={cn(
            "w-4 h-4 text-slate-400 transition-transform duration-200",
            isExpanded && "rotate-180"
          )} />
        )}
      </button>
      
      {/* Expanded Details */}
      <AnimatePresence>
        {isExpanded && !isRouting && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-4">
              {/* Rationale */}
              {rationale && (
                <div>
                  <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                    Why This Mode
                  </h4>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    {rationale}
                  </p>
                </div>
              )}
              
              {/* Complexity Signals */}
              {complexitySignals.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                    Complexity Signals Detected
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {complexitySignals.map((signal, idx) => (
                      <Badge 
                        key={idx} 
                        className="bg-amber-500/10 text-amber-300 border-amber-500/30"
                      >
                        {signal}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Agents by Lane */}
              {activeAgents.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                    Agents Activated
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    {/* Lane A */}
                    <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                      <span className="text-xs text-emerald-400 font-medium">Lane A (Clinical)</span>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {laneAAgents.map((agent) => (
                          <Badge key={agent} className="bg-emerald-500/20 text-emerald-300 text-xs">
                            {agent}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    
                    {/* Lane B */}
                    <div className="p-3 rounded-lg bg-purple-500/5 border border-purple-500/20">
                      <span className="text-xs text-purple-400 font-medium">Lane B (Exploratory)</span>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {laneBAgents.map((agent) => (
                          <Badge key={agent} className="bg-purple-500/20 text-purple-300 text-xs">
                            {agent}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

