"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, Brain, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { AGENT_INFO, AGENT_MODEL_OPTIONS } from "./constants";
import type { AgentConfig } from "./types";

interface AgentRowProps {
  agent: AgentConfig;
  onUpdate: (agent: AgentConfig) => void;
  disabled?: boolean;
}

function AgentRow({ agent, onUpdate, disabled }: AgentRowProps) {
  const info = AGENT_INFO[agent.role];
  
  return (
    <div className={cn(
      "p-3 rounded-lg border transition-colors",
      agent.enabled 
        ? `${info.bgColor} border-slate-700/50` 
        : "bg-slate-900/50 border-slate-800/50 opacity-60"
    )}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Switch
            checked={agent.enabled}
            onCheckedChange={(v) => onUpdate({ ...agent, enabled: v })}
            disabled={disabled}
          />
          <span className={cn("text-sm font-medium", info.color)}>
            {info.label}
          </span>
          <Badge className={cn(
            "text-[10px]",
            info.lane === "A" 
              ? "bg-green-500/20 text-green-300 border-green-500/30" 
              : "bg-purple-500/20 text-purple-300 border-purple-500/30"
          )}>
            Lane {info.lane}
          </Badge>
        </div>
      </div>
      
      <p className="text-xs text-slate-400 mb-2">{info.description}</p>
      
      {agent.enabled && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
        >
          <select
            value={agent.model}
            onChange={(e) => onUpdate({ ...agent, model: e.target.value })}
            disabled={disabled}
            className={cn(
              "w-full h-7 px-2 rounded border bg-slate-900 text-slate-200 text-xs",
              "border-slate-700 focus:border-cyan-500/50 focus:outline-none",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            <optgroup label="⚖️ Balanced">
              {AGENT_MODEL_OPTIONS.filter(m => m.category === "balanced").map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </optgroup>
            <optgroup label="🚀 Powerful">
              {AGENT_MODEL_OPTIONS.filter(m => m.category === "powerful").map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </optgroup>
            <optgroup label="🧠 Deep Reasoning">
              {AGENT_MODEL_OPTIONS.filter(m => m.category === "reasoning").map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </optgroup>
          </select>
        </motion.div>
      )}
    </div>
  );
}

interface AgentConfigSectionProps {
  agents: AgentConfig[];
  onChange: (agents: AgentConfig[]) => void;
  disabled?: boolean;
}

export function AgentConfigSection({ agents, onChange, disabled }: AgentConfigSectionProps) {
  const [expanded, setExpanded] = useState(false);
  
  const enabledCount = agents.filter(a => a.enabled).length;
  const laneACount = agents.filter(a => a.enabled && AGENT_INFO[a.role].lane === "A").length;
  const laneBCount = agents.filter(a => a.enabled && AGENT_INFO[a.role].lane === "B").length;
  
  const updateAgent = (updated: AgentConfig) => {
    onChange(agents.map(a => a.role === updated.role ? updated : a));
  };

  return (
    <Card className="bg-slate-800/30 border-slate-700/50">
      <CardHeader
        className="py-3 px-4 cursor-pointer hover:bg-slate-800/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-medium text-slate-200">Agent Configuration</span>
            <div className="flex items-center gap-1 ml-2">
              <Badge className="text-[10px] bg-green-500/20 text-green-300 border-green-500/30">
                A: {laneACount}
              </Badge>
              <Badge className="text-[10px] bg-purple-500/20 text-purple-300 border-purple-500/30">
                B: {laneBCount}
              </Badge>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">{enabledCount} active</span>
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </div>
      </CardHeader>
      
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ opacity: 0, height: 0 }}
          >
            <CardContent className="pt-0 space-y-3">
              {/* Lane A agents */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs text-green-400 mb-1">
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                  Lane A (Clinical)
                </div>
                {agents
                  .filter(a => AGENT_INFO[a.role].lane === "A")
                  .map(agent => (
                    <AgentRow
                      key={agent.role}
                      agent={agent}
                      onUpdate={updateAgent}
                      disabled={disabled}
                    />
                  ))
                }
              </div>
              
              <div className="border-t border-slate-700/50" />
              
              {/* Lane B agents */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs text-purple-400 mb-1">
                  <span className="w-2 h-2 rounded-full bg-purple-400" />
                  Lane B (Exploratory)
                </div>
                {agents
                  .filter(a => AGENT_INFO[a.role].lane === "B")
                  .map(agent => (
                    <AgentRow
                      key={agent.role}
                      agent={agent}
                      onUpdate={updateAgent}
                      disabled={disabled}
                    />
                  ))
                }
              </div>
              
              {/* Warning if less than 2 agents */}
              {enabledCount < 2 && (
                <div className="rounded-md bg-amber-500/10 border border-amber-500/30 p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-amber-400">
                      At least 2 agents are required for meaningful deliberation.
                    </p>
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

