"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, Search, Shield, Sliders, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";

import {
  RiskToleranceSlider,
  OptionDropdown,
  ModelSelect,
  AgentConfigSection,
  LibrarianConfigSection,
  LearningToggle,
  MODE_OPTIONS,
  TOPOLOGY_OPTIONS,
  TIMEFRAME_OPTIONS,
  DEFAULT_CONFIG,
} from "./config";

import type { ConferenceConfig, ConferenceMode, TopologyType, ConfigPanelProps } from "./config";

// Re-export types and constants for backward compatibility
export type { ConferenceConfig, ConferenceMode, TopologyType, V3ModelConfig, AgentConfig, LibrarianConfig, AgentRoleKey } from "./config";
export { DEFAULT_CONFIG };

export function ConfigPanel({ config, onChange, disabled = false, hasFiles = false }: ConfigPanelProps) {
  const [advancedExpanded, setAdvancedExpanded] = useState(false);
  const [modelsExpanded, setModelsExpanded] = useState(false);

  const updateConfig = (partial: Partial<ConferenceConfig>) => {
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
          <OptionDropdown<ConferenceMode>
            label="Mode Override"
            value={config.modeOverride}
            options={MODE_OPTIONS}
            onChange={(v) => updateConfig({ modeOverride: v })}
            disabled={disabled}
          />
        </CardContent>
      </Card>

      {/* Topology Override */}
      <Card className="bg-slate-800/30 border-slate-700/50">
        <CardContent className="pt-4">
          <OptionDropdown<TopologyType>
            label="Topology Override"
            value={config.topologyOverride}
            options={TOPOLOGY_OPTIONS}
            onChange={(v) => updateConfig({ topologyOverride: v })}
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
                  scoutTimeframe: e.target.value as ConferenceConfig["scoutTimeframe"] 
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

      {/* Agent Configuration */}
      <AgentConfigSection
        agents={config.agents}
        onChange={(agents) => updateConfig({ agents })}
        disabled={disabled}
      />

      {/* Librarian Configuration */}
      <LibrarianConfigSection
        config={config.librarian}
        onChange={(librarian) => updateConfig({ librarian })}
        disabled={disabled}
        hasFiles={hasFiles}
      />

      {/* Learning Toggle */}
      <LearningToggle
        enabled={config.enableLearning}
        onChange={(v) => updateConfig({ enableLearning: v })}
        disabled={disabled}
      />

      {/* Model Configuration (v3 only) */}
      <AnimatePresence>
        {config.enableLearning && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <Card className="bg-purple-900/10 border-purple-500/30">
              <CardHeader
                className="py-3 px-4 cursor-pointer hover:bg-purple-900/20 transition-colors"
                onClick={() => setModelsExpanded(!modelsExpanded)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-purple-400" />
                    <span className="text-sm font-medium text-purple-300">Component Models</span>
                  </div>
                  {modelsExpanded ? (
                    <ChevronUp className="w-4 h-4 text-purple-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-purple-400" />
                  )}
                </div>
              </CardHeader>
              
              <AnimatePresence>
                {modelsExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                  >
                    <CardContent className="pt-0 space-y-4">
                      <div className="space-y-4">
                        <ModelSelect
                          componentKey="router_model"
                          value={config.modelConfig.router_model}
                          onChange={(v) => updateConfig({ 
                            modelConfig: { ...config.modelConfig, router_model: v } 
                          })}
                          disabled={disabled}
                        />
                        
                        <ModelSelect
                          componentKey="classifier_model"
                          value={config.modelConfig.classifier_model}
                          onChange={(v) => updateConfig({ 
                            modelConfig: { ...config.modelConfig, classifier_model: v } 
                          })}
                          disabled={disabled}
                        />
                        
                        <ModelSelect
                          componentKey="surgeon_model"
                          value={config.modelConfig.surgeon_model}
                          onChange={(v) => updateConfig({ 
                            modelConfig: { ...config.modelConfig, surgeon_model: v } 
                          })}
                          disabled={disabled}
                        />
                        
                        <ModelSelect
                          componentKey="validator_model"
                          value={config.modelConfig.validator_model}
                          onChange={(v) => updateConfig({ 
                            modelConfig: { ...config.modelConfig, validator_model: v } 
                          })}
                          disabled={disabled}
                        />
                      </div>

                      <div className="rounded-md bg-slate-800/50 border border-slate-700/50 p-3">
                        <div className="flex items-start gap-2">
                          <Info className="w-3.5 h-3.5 text-purple-400 mt-0.5 flex-shrink-0" />
                          <p className="text-xs text-slate-400">
                            Fast models (Haiku, Mini) work well for classification. Use powerful models 
                            (Sonnet, GPT-4) for extraction where nuance matters.
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </motion.div>
                )}
              </AnimatePresence>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

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
