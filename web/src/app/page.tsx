"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Square, 
  RefreshCw,
  Zap,
  Activity,
  Sparkles,
} from "lucide-react";

import { Header } from "@/components/conference/Header";
import { QueryInput, FileUpload } from "@/components/conference/QueryInput";
import { ConfigPanel, type ConferenceConfig } from "@/components/conference/ConfigPanel";
import { PatientContextForm } from "@/components/conference/PatientContextForm";
import { AgentCard, AgentCardCompact } from "@/components/conference/AgentCard";
import { MiniTimeline } from "@/components/conference/Timeline";
import { Results } from "@/components/conference/Results";
import { TwoLaneResults } from "@/components/conference/TwoLaneResults";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { useConference } from "@/hooks/useConference";
import { apiClient, type PatientContext, type V2ConferenceResult } from "@/lib/api";
import { cn } from "@/lib/utils";

const DEFAULT_CONFIG: ConferenceConfig = {
  agents: [
    { role: "advocate", model: "anthropic/claude-sonnet-4" },
    { role: "empiricist", model: "anthropic/claude-sonnet-4" },
    { role: "mechanist", model: "anthropic/claude-sonnet-4" },
    { role: "skeptic", model: "anthropic/claude-sonnet-4" },
  ],
  arbitratorModel: "anthropic/claude-sonnet-4",
  numRounds: 2,
  topology: "free_discussion",
  enableGrounding: true,
  enableFragility: false,
  fragilityTests: 3,
  fragilityModel: "anthropic/claude-sonnet-4",
  librarianModel: "google/gemini-3-pro-preview",
  librarianMaxQueries: 3,
};

export default function Home() {
  // Config state
  const [config, setConfig] = useState<ConferenceConfig>(DEFAULT_CONFIG);

  // v2.1 mode state
  const [enableV2, setEnableV2] = useState(false);
  const [patientContext, setPatientContext] = useState<PatientContext>({});
  const [v2Result, setV2Result] = useState<V2ConferenceResult | null>(null);

  // File upload state
  const [files, setFiles] = useState<File[]>([]);

  // Connection state
  const [isConnected, setIsConnected] = useState(true);

  // Expanded agent state
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  // Conference hook
  const { state: conferenceState, startConference, startV2Conference, stopConference } = useConference();

  // Check API connection on mount
  useEffect(() => {
    apiClient.healthCheck().then(setIsConnected);
  }, []);

  // Handle conference start
  const handleStartConference = useCallback(
    async (query: string) => {
      // Build request
      const request = {
        query,
        agents: config.agents,
        arbitrator_model: config.arbitratorModel,
        num_rounds: config.numRounds,
        topology: config.topology,
        enable_grounding: config.enableGrounding,
        enable_fragility: config.enableFragility,
        fragility_tests: config.fragilityTests,
        fragility_model: config.fragilityModel,
        librarian: files.length > 0
          ? {
              model: config.librarianModel,
              max_queries_per_turn: config.librarianMaxQueries,
            }
          : undefined,
        // v2.1 options
        patient_context: enableV2 ? patientContext : undefined,
        enable_v2: enableV2,
        enable_scout: enableV2,
        enable_routing: enableV2,
      };

      if (enableV2) {
        const result = await startV2Conference(request);
        if (result) {
          setV2Result(result as V2ConferenceResult);
        }
      } else {
        await startConference(request);
      }
    },
    [config, files, enableV2, patientContext, startConference, startV2Conference]
  );

  // Handle reset
  const handleReset = useCallback(() => {
    stopConference();
    setFiles([]);
    setV2Result(null);
    setPatientContext({});
  }, [stopConference]);

  const isRunning = conferenceState.status === "running" || conferenceState.status === "starting";
  const isComplete = conferenceState.status === "complete";
  const hasError = conferenceState.status === "error";

  return (
    <div className="min-h-screen">
      {/* Header */}
      <Header
        isConnected={isConnected}
        conferenceStatus={conferenceState.status === "starting" ? "running" : conferenceState.status}
      />

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-12 gap-6">
          {/* Left column - Config */}
          <aside className="col-span-4">
            <div className="sticky top-24 space-y-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
                  Configuration
                </h2>
                {isComplete && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleReset}
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    New
                  </Button>
                )}
              </div>
              <ConfigPanel
                config={config}
                onChange={setConfig}
                disabled={isRunning}
              />
            </div>
          </aside>

          {/* Center column - Main content */}
          <div className="col-span-8 space-y-6">
            {/* Query input section */}
            {!isRunning && !isComplete && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
              >
                <Card variant="glass" glow="cyan">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-accent-primary/20 border border-accent-primary/30">
                        <Zap className="w-5 h-5 text-accent-primary" />
                      </div>
                      <div>
                        <CardTitle>Clinical Scenario</CardTitle>
                        <p className="text-sm text-slate-500 mt-1">
                          Describe the case for multi-agent deliberation
                        </p>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-6">
                    <QueryInput
                      onSubmit={handleStartConference}
                      loading={conferenceState.status === "starting"}
                    />

                    {/* File upload section */}
                    <div className="pt-4 border-t border-white/5">
                      <h3 className="text-sm font-medium text-slate-300 mb-3">
                        Case Documents (optional)
                      </h3>
                      <FileUpload
                        files={files}
                        onFilesChange={setFiles}
                      />
                      {files.length > 0 && (
                        <p className="text-xs text-slate-500 mt-2">
                          📚 Librarian will analyze these documents and make them
                          available to agents
                        </p>
                      )}
                    </div>

                    {/* v2.1 Mode Toggle */}
                    <div className="pt-4 border-t border-white/5">
                      <div className="flex items-center justify-between p-4 rounded-lg bg-gradient-to-r from-violet-500/10 to-cyan-500/10 border border-violet-500/20">
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-violet-500/20">
                            <Sparkles className="w-4 h-4 text-violet-400" />
                          </div>
                          <div>
                            <h4 className="text-sm font-medium text-slate-200">v2.1 Adversarial MoE</h4>
                            <p className="text-xs text-slate-400">
                              Parallel lanes, Scout literature search, cross-examination
                            </p>
                          </div>
                        </div>
                        <Switch
                          checked={enableV2}
                          onCheckedChange={setEnableV2}
                        />
                      </div>
                    </div>

                    {/* Patient Context (v2 only) */}
                    {enableV2 && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="pt-4 border-t border-white/5"
                      >
                        <PatientContextForm
                          value={patientContext}
                          onChange={setPatientContext}
                        />
                      </motion.div>
                    )}

                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Running state */}
            {isRunning && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-6"
              >
                {/* Progress header */}
                <Card variant="glass" glow="cyan">
                  <CardContent className="py-6">
                    <div className="flex items-center justify-between mb-4">
                      <MiniTimeline
                        currentRound={conferenceState.currentRound}
                        totalRounds={conferenceState.totalRounds}
                        phase={conferenceState.phase}
                      />

                      <Button
                        variant="danger"
                        size="sm"
                        onClick={stopConference}
                      >
                        <Square className="w-4 h-4 mr-2" />
                        Stop
                      </Button>
                    </div>

                    <Progress
                      value={conferenceState.progress}
                      variant="gradient"
                      size="md"
                    />
                  </CardContent>
                </Card>

                {/* Agent grid */}
                <div>
                  <h3 className="text-sm font-medium text-slate-400 mb-4 flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    Active Agents
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    {Object.values(conferenceState.agents).map((agent) => (
                      <AgentCard
                        key={agent.role}
                        agent={agent}
                        expanded={expandedAgent === agent.role}
                        onToggleExpand={() => 
                          setExpandedAgent(expandedAgent === agent.role ? null : agent.role)
                        }
                      />
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Error state */}
            {hasError && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <Card variant="bordered" className="border-red-500/30 bg-red-500/5">
                  <CardContent className="py-6">
                    <div className="flex items-center gap-4">
                      <div className="p-3 rounded-full bg-red-500/10">
                        <Activity className="w-6 h-6 text-red-400" />
                      </div>
                      <div>
                        <h3 className="text-lg font-medium text-red-400">
                          Conference Error
                        </h3>
                        <p className="text-sm text-slate-400 mt-1">
                          {conferenceState.error}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        className="ml-auto"
                        onClick={handleReset}
                      >
                        Try Again
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Results */}
            {isComplete && (
              <>
                {enableV2 && v2Result ? (
                  <TwoLaneResults result={v2Result} />
                ) : conferenceState.result && (
                  <Results result={conferenceState.result} />
                )}
              </>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 mt-16">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <p>AI Case Conference System</p>
            <p>
              Powered by{" "}
              <a
                href="https://openrouter.ai"
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent-primary hover:underline"
              >
                OpenRouter
              </a>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
