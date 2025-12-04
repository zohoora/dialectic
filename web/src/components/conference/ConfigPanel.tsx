"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Settings2, 
  ChevronDown, 
  Users, 
  Layers, 
  FlaskConical,
  BookOpen,
  Zap
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { AgentConfig } from "@/lib/api";

// Available models
const MODELS = [
  { value: "anthropic/claude-sonnet-4", label: "Claude Sonnet 4" },
  { value: "anthropic/claude-opus-4", label: "Claude Opus 4" },
  { value: "openai/gpt-4o", label: "GPT-4o" },
  { value: "openai/o3", label: "O3" },
  { value: "google/gemini-2.5-pro", label: "Gemini 2.5 Pro" },
];

// Available topologies with minimum rounds
const TOPOLOGIES = [
  { value: "free_discussion", label: "Free Discussion", description: "Open deliberation, all agents see all responses", minRounds: 1 },
  { value: "oxford_debate", label: "Oxford Debate", description: "Structured pro/con debate with judge", minRounds: 2 },
  { value: "delphi_method", label: "Delphi Method", description: "Anonymous rounds to reduce bias", minRounds: 2 },
  { value: "socratic_spiral", label: "Socratic Spiral", description: "Questions → Answers → Synthesis", minRounds: 3 },
  { value: "red_team", label: "Red Team", description: "Adversarial review and stress testing", minRounds: 2 },
];

// Helper to get minimum rounds for a topology
const getMinRounds = (topology: string): number => {
  return TOPOLOGIES.find(t => t.value === topology)?.minRounds || 1;
};

// Agent roles
const AGENT_ROLES = [
  { role: "advocate", label: "Advocate", description: "Prioritizes patient-centered outcomes" },
  { role: "empiricist", label: "Empiricist", description: "Evidence-based reasoning" },
  { role: "mechanist", label: "Mechanist", description: "Pathophysiology focus" },
  { role: "skeptic", label: "Skeptic", description: "Devil's advocate, challenges assumptions" },
  { role: "patient_voice", label: "Patient Voice", description: "Quality of life perspective" },
];

export interface ConferenceConfig {
  agents: AgentConfig[];
  arbitratorModel: string;
  numRounds: number;
  topology: string;
  enableGrounding: boolean;
  enableFragility: boolean;
  fragilityTests: number;
  fragilityModel: string;
  librarianModel: string;
  librarianMaxQueries: number;
}

interface ConfigPanelProps {
  config: ConferenceConfig;
  onChange: (config: ConferenceConfig) => void;
  disabled?: boolean;
}

export function ConfigPanel({ config, onChange, disabled }: ConfigPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["agents"])
  );

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const updateConfig = (updates: Partial<ConferenceConfig>) => {
    onChange({ ...config, ...updates });
  };

  const toggleAgent = (role: string) => {
    const existing = config.agents.find((a) => a.role === role);
    if (existing) {
      updateConfig({
        agents: config.agents.filter((a) => a.role !== role),
      });
    } else {
      updateConfig({
        agents: [
          ...config.agents,
          { role, model: "anthropic/claude-sonnet-4" },
        ],
      });
    }
  };

  const updateAgentModel = (role: string, model: string) => {
    updateConfig({
      agents: config.agents.map((a) =>
        a.role === role ? { ...a, model } : a
      ),
    });
  };

  return (
    <div className="space-y-4">
      {/* Agents Section */}
      <ConfigSection
        title="Agents"
        icon={Users}
        expanded={expandedSections.has("agents")}
        onToggle={() => toggleSection("agents")}
        badge={`${config.agents.length} selected`}
      >
        <div className="space-y-3">
          {AGENT_ROLES.map((agent) => {
            const isSelected = config.agents.some((a) => a.role === agent.role);
            const selectedAgent = config.agents.find(
              (a) => a.role === agent.role
            );

            return (
              <div
                key={agent.role}
                className={cn(
                  "p-3 rounded-lg border transition-all",
                  isSelected
                    ? "bg-void-200/50 border-accent-primary/30"
                    : "bg-void-200/20 border-white/5 opacity-60"
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <Switch
                      checked={isSelected}
                      onChange={() => toggleAgent(agent.role)}
                      disabled={disabled || (isSelected && config.agents.length <= 2)}
                    />
                    <div>
                      <p className="text-sm font-medium text-slate-200">
                        {agent.label}
                      </p>
                      <p className="text-xs text-slate-500">
                        {agent.description}
                      </p>
                    </div>
                  </div>
                </div>

                {isSelected && (
                  <Select
                    value={selectedAgent?.model || "anthropic/claude-sonnet-4"}
                    onChange={(e) => updateAgentModel(agent.role, e.target.value)}
                    options={MODELS}
                    disabled={disabled}
                  />
                )}
              </div>
            );
          })}
        </div>
      </ConfigSection>

      {/* Topology Section */}
      <ConfigSection
        title="Topology"
        icon={Layers}
        expanded={expandedSections.has("topology")}
        onToggle={() => toggleSection("topology")}
        badge={TOPOLOGIES.find((t) => t.value === config.topology)?.label}
      >
        <div className="space-y-2">
          {TOPOLOGIES.map((topology) => (
            <button
              key={topology.value}
              onClick={() => {
                // When topology changes, enforce its minimum rounds
                const minRounds = topology.minRounds;
                const newRounds = Math.max(config.numRounds, minRounds);
                updateConfig({ 
                  topology: topology.value,
                  numRounds: newRounds,
                });
              }}
              disabled={disabled}
              className={cn(
                "w-full p-3 rounded-lg border text-left transition-all",
                config.topology === topology.value
                  ? "bg-accent-primary/10 border-accent-primary/30"
                  : "bg-void-200/20 border-white/5 hover:bg-void-200/30"
              )}
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-slate-200">
                  {topology.label}
                </p>
                <Badge variant="outline" className="text-xs">
                  {topology.minRounds}+ rounds
                </Badge>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {topology.description}
              </p>
            </button>
          ))}
        </div>
      </ConfigSection>

      {/* Deliberation Section */}
      <ConfigSection
        title="Deliberation"
        icon={Settings2}
        expanded={expandedSections.has("deliberation")}
        onToggle={() => toggleSection("deliberation")}
      >
        <div className="space-y-4">
          {(() => {
            const minRounds = getMinRounds(config.topology);
            return (
              <Slider
                label={`Rounds (min ${minRounds} for ${TOPOLOGIES.find(t => t.value === config.topology)?.label})`}
                value={config.numRounds}
                min={minRounds}
                max={5}
                onChange={(e) =>
                  updateConfig({ numRounds: parseInt(e.target.value) })
                }
                disabled={disabled}
              />
            );
          })()}

          <div>
            <label className="text-sm text-slate-400 block mb-2">
              Arbitrator Model
            </label>
            <Select
              value={config.arbitratorModel}
              onChange={(e) => updateConfig({ arbitratorModel: e.target.value })}
              options={MODELS}
              disabled={disabled}
            />
          </div>
        </div>
      </ConfigSection>

      {/* Grounding Section */}
      <ConfigSection
        title="Evidence Grounding"
        icon={BookOpen}
        expanded={expandedSections.has("grounding")}
        onToggle={() => toggleSection("grounding")}
        badge={config.enableGrounding ? "On" : "Off"}
      >
        <div className="space-y-3">
          <Switch
            label="Verify citations via PubMed"
            checked={config.enableGrounding}
            onChange={(e) =>
              updateConfig({ enableGrounding: e.target.checked })
            }
            disabled={disabled}
          />
          <p className="text-xs text-slate-500">
            Cross-references cited studies with PubMed to verify accuracy
          </p>
        </div>
      </ConfigSection>

      {/* Fragility Testing Section */}
      <ConfigSection
        title="Fragility Testing"
        icon={FlaskConical}
        expanded={expandedSections.has("fragility")}
        onToggle={() => toggleSection("fragility")}
        badge={config.enableFragility ? "On" : "Off"}
      >
        <div className="space-y-4">
          <Switch
            label="Enable stress testing"
            checked={config.enableFragility}
            onChange={(e) =>
              updateConfig({ enableFragility: e.target.checked })
            }
            disabled={disabled}
          />

          {config.enableFragility && (
            <>
              <Slider
                label="Number of tests"
                value={config.fragilityTests}
                min={1}
                max={10}
                onChange={(e) =>
                  updateConfig({ fragilityTests: parseInt(e.target.value) })
                }
                disabled={disabled}
              />

              <div>
                <label className="text-sm text-slate-400 block mb-2">
                  Testing Model
                </label>
                <Select
                  value={config.fragilityModel}
                  onChange={(e) =>
                    updateConfig({ fragilityModel: e.target.value })
                  }
                  options={MODELS}
                  disabled={disabled}
                />
              </div>
            </>
          )}
        </div>
      </ConfigSection>

      {/* Librarian Section */}
      <ConfigSection
        title="Librarian"
        icon={Zap}
        expanded={expandedSections.has("librarian")}
        onToggle={() => toggleSection("librarian")}
      >
        <div className="space-y-4">
          <div>
            <label className="text-sm text-slate-400 block mb-2">
              Analysis Model
            </label>
            <Select
              value={config.librarianModel}
              onChange={(e) => updateConfig({ librarianModel: e.target.value })}
              options={[
                { value: "google/gemini-3-pro-preview", label: "Gemini 3 Pro" },
                { value: "anthropic/claude-opus-4", label: "Claude Opus 4.5" },
              ]}
              disabled={disabled}
            />
          </div>

          <Slider
            label="Max queries per turn"
            value={config.librarianMaxQueries}
            min={1}
            max={10}
            onChange={(e) =>
              updateConfig({ librarianMaxQueries: parseInt(e.target.value) })
            }
            disabled={disabled}
          />
        </div>
      </ConfigSection>
    </div>
  );
}

// Collapsible section component
function ConfigSection({
  title,
  icon: Icon,
  children,
  expanded,
  onToggle,
  badge,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
  badge?: string;
}) {
  return (
    <Card variant="bordered" className="overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-4 h-4 text-accent-primary" />
          <span className="text-sm font-medium text-slate-200">{title}</span>
          {badge && (
            <Badge variant="outline" className="text-xs">
              {badge}
            </Badge>
          )}
        </div>
        <ChevronDown
          className={cn(
            "w-4 h-4 text-slate-400 transition-transform",
            expanded && "rotate-180"
          )}
        />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <CardContent className="pt-0 pb-4 px-4 border-t border-white/5">
              {children}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

