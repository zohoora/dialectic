"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  ChevronDown, 
  ChevronUp, 
  Sliders, 
  Search, 
  Shield, 
  Beaker,
  AlertTriangle,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";

// ============================================================================
// TYPES
// ============================================================================

export type ConferenceMode = 
  | "auto" 
  | "STANDARD_CARE" 
  | "COMPLEX_DILEMMA" 
  | "NOVEL_RESEARCH" 
  | "DIAGNOSTIC_PUZZLE";

export interface V21Config {
  riskTolerance: number; // 0.0 - 1.0
  modeOverride: ConferenceMode;
  enableScout: boolean;
  scoutTimeframe: "6_months" | "12_months" | "24_months" | "all_time";
  enableFragilityTesting: boolean;
  fragilityTests: number;
}

interface ConfigPanelV21Props {
  config: V21Config;
  onChange: (config: V21Config) => void;
  disabled?: boolean;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const MODE_OPTIONS: Array<{
  value: ConferenceMode;
  label: string;
  description: string;
  icon: React.ElementType;
  color: string;
}> = [
  { 
    value: "auto", 
    label: "Auto (Router decides)", 
    description: "Recommended - system analyzes query complexity",
    icon: Sliders,
    color: "text-cyan-400",
  },
  { 
    value: "STANDARD_CARE", 
    label: "Standard Care", 
    description: "Guideline check, minimal deliberation",
    icon: Shield,
    color: "text-slate-400",
  },
  { 
    value: "COMPLEX_DILEMMA", 
    label: "Complex Dilemma", 
    description: "Full team, all lanes",
    icon: AlertTriangle,
    color: "text-amber-400",
  },
  { 
    value: "NOVEL_RESEARCH", 
    label: "Novel Research", 
    description: "Emphasis on Speculator",
    icon: Beaker,
    color: "text-purple-400",
  },
  { 
    value: "DIAGNOSTIC_PUZZLE", 
    label: "Diagnostic Puzzle", 
    description: "Emphasis on differentials",
    icon: Search,
    color: "text-blue-400",
  },
];

const TIMEFRAME_OPTIONS = [
  { value: "6_months", label: "Last 6 months" },
  { value: "12_months", label: "Last 12 months" },
  { value: "24_months", label: "Last 24 months" },
  { value: "all_time", label: "All time" },
] as const;

// ============================================================================
// RISK TOLERANCE SLIDER
// ============================================================================

interface RiskToleranceSliderProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}

function RiskToleranceSlider({ value, onChange, disabled }: RiskToleranceSliderProps) {
  const getLabel = (v: number) => {
    if (v < 0.3) return "Conservative";
    if (v < 0.7) return "Balanced";
    return "Exploratory";
  };
  
  const getDescription = (v: number) => {
    if (v < 0.3) return "Prioritize established guidelines. Speculator minimized.";
    if (v < 0.7) return "Full conference with balanced weighting between clinical evidence and exploratory ideas.";
    return "Weight novel approaches. Speculator emphasized.";
  };

  const getColor = (v: number) => {
    if (v < 0.3) return "bg-green-500";
    if (v < 0.7) return "bg-amber-500";
    return "bg-purple-500";
  };
  
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs text-slate-400 uppercase tracking-wider">
          Risk Tolerance
        </label>
        <span className={cn(
          "text-xs font-medium px-2 py-0.5 rounded-full",
          value < 0.3 && "bg-green-500/20 text-green-400",
          value >= 0.3 && value < 0.7 && "bg-amber-500/20 text-amber-400",
          value >= 0.7 && "bg-purple-500/20 text-purple-400"
        )}>
          {getLabel(value)}
        </span>
      </div>
      
      <div className="space-y-2">
        <div className="flex items-center justify-between text-[10px] text-slate-500">
          <span>Conservative</span>
          <span>Exploratory</span>
        </div>
        
        <div className="relative">
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={value}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            disabled={disabled}
            className={cn(
              "w-full h-2 bg-slate-700 rounded-full appearance-none cursor-pointer",
              "[&::-webkit-slider-thumb]:appearance-none",
              "[&::-webkit-slider-thumb]:w-4",
              "[&::-webkit-slider-thumb]:h-4",
              "[&::-webkit-slider-thumb]:rounded-full",
              "[&::-webkit-slider-thumb]:bg-white",
              "[&::-webkit-slider-thumb]:shadow-lg",
              "[&::-webkit-slider-thumb]:cursor-pointer",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          />
          {/* Progress fill */}
          <div 
            className={cn("absolute top-0 left-0 h-2 rounded-full pointer-events-none", getColor(value))}
            style={{ width: `${value * 100}%` }}
          />
        </div>
        
        <div className="text-center">
          <span className="text-sm font-mono text-slate-300">{value.toFixed(1)}</span>
        </div>
      </div>
      
      <div className="rounded-md bg-slate-800/50 border border-slate-700/50 p-3">
        <div className="flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-slate-400">{getDescription(value)}</p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MODE OVERRIDE DROPDOWN
// ============================================================================

interface ModeOverrideDropdownProps {
  value: ConferenceMode;
  onChange: (value: ConferenceMode) => void;
  disabled?: boolean;
}

function ModeOverrideDropdown({ value, onChange, disabled }: ModeOverrideDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const selectedOption = MODE_OPTIONS.find(opt => opt.value === value) || MODE_OPTIONS[0];
  const Icon = selectedOption.icon;
  
  return (
    <div className="space-y-2">
      <label className="text-xs text-slate-400 uppercase tracking-wider">
        Mode Override
      </label>
      
      <div className="relative">
        <button
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={cn(
            "w-full flex items-center justify-between px-3 py-2.5 rounded-lg",
            "bg-slate-800 border border-slate-700 text-left",
            "hover:border-slate-600 transition-colors",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        >
          <div className="flex items-center gap-2">
            <Icon className={cn("w-4 h-4", selectedOption.color)} />
            <div>
              <span className="text-sm text-slate-200">{selectedOption.label}</span>
            </div>
          </div>
          <ChevronDown className={cn(
            "w-4 h-4 text-slate-400 transition-transform",
            isOpen && "rotate-180"
          )} />
        </button>
        
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-full left-0 right-0 mt-1 z-50 rounded-lg bg-slate-800 border border-slate-700 shadow-xl overflow-hidden"
            >
              {MODE_OPTIONS.map((option) => {
                const OptionIcon = option.icon;
                return (
                  <button
                    key={option.value}
                    onClick={() => {
                      onChange(option.value);
                      setIsOpen(false);
                    }}
                    className={cn(
                      "w-full flex items-start gap-3 px-3 py-3 text-left",
                      "hover:bg-slate-700/50 transition-colors",
                      option.value === value && "bg-slate-700/30"
                    )}
                  >
                    <OptionIcon className={cn("w-4 h-4 mt-0.5", option.color)} />
                    <div>
                      <div className="text-sm text-slate-200">{option.label}</div>
                      <div className="text-xs text-slate-500">{option.description}</div>
                    </div>
                    {option.value === value && (
                      <span className="ml-auto text-cyan-400">✓</span>
                    )}
                  </button>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ============================================================================
// CONFIG PANEL V2.1
// ============================================================================

export function ConfigPanelV21({ config, onChange, disabled = false }: ConfigPanelV21Props) {
  const [advancedExpanded, setAdvancedExpanded] = useState(false);

  const updateConfig = (partial: Partial<V21Config>) => {
    onChange({ ...config, ...partial });
  };

  return (
    <div className="space-y-4">
      {/* Risk Tolerance */}
      <Card className="bg-slate-800/30 border-slate-700/50">
        <CardContent className="pt-4">
          <RiskToleranceSlider
            value={config.riskTolerance}
            onChange={(v) => updateConfig({ riskTolerance: v })}
            disabled={disabled}
          />
        </CardContent>
      </Card>

      {/* Mode Override */}
      <Card className="bg-slate-800/30 border-slate-700/50">
        <CardContent className="pt-4">
          <ModeOverrideDropdown
            value={config.modeOverride}
            onChange={(v) => updateConfig({ modeOverride: v })}
            disabled={disabled}
          />
        </CardContent>
      </Card>

      {/* Scout Settings */}
      <Card className="bg-slate-800/30 border-slate-700/50">
        <CardContent className="pt-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4 text-lime-400" />
              <span className="text-sm text-slate-200">Scout Literature</span>
            </div>
            <Switch
              checked={config.enableScout}
              onCheckedChange={(v) => updateConfig({ enableScout: v })}
              disabled={disabled}
            />
          </div>
          
          {config.enableScout && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <label className="text-xs text-slate-400 mb-1.5 block">
                Search timeframe
              </label>
              <select
                value={config.scoutTimeframe}
                onChange={(e) => updateConfig({ 
                  scoutTimeframe: e.target.value as V21Config["scoutTimeframe"] 
                })}
                disabled={disabled}
                className={cn(
                  "w-full h-9 px-3 rounded-md border bg-slate-900 text-slate-200 text-sm",
                  "border-slate-700 focus:border-cyan-500/50 focus:outline-none",
                  disabled && "opacity-50 cursor-not-allowed"
                )}
              >
                {TIMEFRAME_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* Fragility Testing */}
      <Card className="bg-slate-800/30 border-slate-700/50">
        <CardContent className="pt-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-amber-400" />
              <span className="text-sm text-slate-200">Fragility Testing</span>
            </div>
            <Switch
              checked={config.enableFragilityTesting}
              onCheckedChange={(v) => updateConfig({ enableFragilityTesting: v })}
              disabled={disabled}
            />
          </div>
          
          {config.enableFragilityTesting && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-2"
            >
              <label className="text-xs text-slate-400 mb-1.5 block">
                Number of perturbations
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="3"
                  max="10"
                  value={config.fragilityTests}
                  onChange={(e) => updateConfig({ fragilityTests: parseInt(e.target.value) })}
                  disabled={disabled}
                  className="flex-1 h-2 bg-slate-700 rounded-full appearance-none cursor-pointer"
                />
                <span className="text-sm font-mono text-slate-300 w-6 text-center">
                  {config.fragilityTests}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                More tests = higher confidence but longer runtime
              </p>
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* Advanced Section */}
      <Card className="bg-slate-800/30 border-slate-700/50">
        <CardHeader
          className="py-3 px-4 cursor-pointer hover:bg-slate-800/50 transition-colors"
          onClick={() => setAdvancedExpanded(!advancedExpanded)}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-200">Advanced</span>
            {advancedExpanded ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </CardHeader>
        
        <AnimatePresence>
          {advancedExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
            >
              <CardContent className="pt-0 space-y-4">
                <div className="space-y-2">
                  <label className="text-xs text-slate-400">Scout Sources</label>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input type="checkbox" defaultChecked className="rounded bg-slate-700 border-slate-600" />
                      PubMed
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input type="checkbox" defaultChecked className="rounded bg-slate-700 border-slate-600" />
                      bioRxiv / medRxiv (preprints)
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input type="checkbox" className="rounded bg-slate-700 border-slate-600" />
                      Cochrane Library
                    </label>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <label className="text-xs text-slate-400">Grounding</label>
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input type="checkbox" defaultChecked className="rounded bg-slate-700 border-slate-600" />
                    Verify all citations
                  </label>
                </div>
                
                <div className="space-y-2">
                  <label className="text-xs text-slate-400">Experience Library</label>
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input type="checkbox" defaultChecked className="rounded bg-slate-700 border-slate-600" />
                    Check for relevant heuristics
                  </label>
                </div>
              </CardContent>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </div>
  );
}

// ============================================================================
// DEFAULT CONFIG
// ============================================================================

export const DEFAULT_V21_CONFIG: V21Config = {
  riskTolerance: 0.5,
  modeOverride: "auto",
  enableScout: true,
  scoutTimeframe: "12_months",
  enableFragilityTesting: false,
  fragilityTests: 5,
};

