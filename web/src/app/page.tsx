"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Square, 
  RefreshCw,
  Zap,
  Activity,
  Sparkles,
  FileText,
  Terminal,
  Layers,
  GitBranch,
} from "lucide-react";

import { Header } from "@/components/conference/Header";
import { QueryInput, FileUpload } from "@/components/conference/QueryInput";
import { ConfigPanel, type ConferenceConfig } from "@/components/conference/ConfigPanel";
import { ConfigPanelV21, DEFAULT_V21_CONFIG, type V21Config } from "@/components/conference/ConfigPanelV21";
import { PatientContextForm } from "@/components/conference/PatientContextForm";
import { AgentCard } from "@/components/conference/AgentCard";
import { MiniTimeline } from "@/components/conference/Timeline";
import { Results } from "@/components/conference/Results";
import { SessionHistoryPanel } from "@/components/conference/SessionHistoryPanel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { VersionToggle, VersionBadge, type ConferenceVersion } from "@/components/ui/VersionToggle";
import { useConference } from "@/hooks/useConference";
import { apiClient, type PatientContext, type V2ConferenceResult, type ConferenceResult } from "@/lib/api";
import { saveSession, type StoredSession } from "@/lib/sessionStorage";
import { cn } from "@/lib/utils";

// v2.1 Components
import {
  RoutingDecisionBar,
  ScoutFindingsPanel,
  LaneContainer,
  AgentCardV2,
  SynthesisView,
  FragilityProfile,
} from "@/components/conference/v2";

// Activity Feed for real-time feedback
import { ActivityFeed, type ActivityEvent } from "@/components/conference/feedback/ActivityFeed";

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

// ============================================================================
// V2 RESULTS DISPLAY
// ============================================================================

function V2ResultsDisplay({ result }: { result: V2ConferenceResult }) {
  if (!result) {
    return <div className="text-red-500">V2 Result is null!</div>;
  }
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Routing Decision Bar */}
      {result.routing && (
        <RoutingDecisionBar
          mode={result.routing.mode as "STANDARD_CARE" | "COMPLEX_DILEMMA" | "NOVEL_RESEARCH" | "DIAGNOSTIC_PUZZLE"}
          agentCount={result.routing.active_agents?.length || 0}
          scoutActive={result.routing.activate_scout || false}
          riskProfile={0.5}
          rationale={result.routing.rationale}
          complexitySignals={result.routing.complexity_signals || []}
          activeAgents={result.routing.active_agents || []}
        />
      )}
      
      {/* Scout Findings */}
      {result.scout_report && !result.scout_report.is_empty && (
        <ScoutFindingsPanel
          report={{
            is_empty: result.scout_report.is_empty,
            query_keywords: result.scout_report.query_keywords || [],
            total_results_found: result.scout_report.total_found || 0,
            meta_analyses: (result.scout_report.meta_analyses || []).map(c => ({
              title: c.title || "Untitled",
              authors: c.authors || [],
              journal: c.journal || "Unknown Journal",
              year: c.year || new Date().getFullYear(),
              pmid: c.pmid,
              evidence_grade: (c.evidence_grade || "meta_analysis") as "meta_analysis" | "rct_large" | "rct_small" | "observational" | "preprint" | "conflicting",
              key_finding: c.key_finding || "",
            })),
            high_quality_rcts: (result.scout_report.high_quality_rcts || []).map(c => ({
              title: c.title || "Untitled",
              authors: c.authors || [],
              journal: c.journal || "Unknown Journal",
              year: c.year || new Date().getFullYear(),
              pmid: c.pmid,
              evidence_grade: (c.evidence_grade || "rct_large") as "meta_analysis" | "rct_large" | "rct_small" | "observational" | "preprint" | "conflicting",
              key_finding: c.key_finding || "",
            })),
            preliminary_evidence: (result.scout_report.preliminary_evidence || []).map(c => ({
              title: c.title || "Untitled",
              authors: c.authors || [],
              journal: c.journal || "Unknown Journal",
              year: c.year || new Date().getFullYear(),
              pmid: c.pmid,
              evidence_grade: (c.evidence_grade || "observational") as "meta_analysis" | "rct_large" | "rct_small" | "observational" | "preprint" | "conflicting",
              key_finding: c.key_finding || "",
            })),
            conflicting_evidence: (result.scout_report.conflicting_evidence || []).map(c => ({
              title: c.title || "Untitled",
              authors: c.authors || [],
              journal: c.journal || "Unknown Journal",
              year: c.year || new Date().getFullYear(),
              pmid: c.pmid,
              evidence_grade: "conflicting" as const,
              key_finding: c.key_finding || "",
            })),
          }}
        />
      )}
      
      {/* Two-Lane Agent Responses */}
      {result.lane_a && (
        <div className={cn(
          "grid gap-6",
          result.lane_b?.responses?.length ? "grid-cols-1 lg:grid-cols-2" : "grid-cols-1"
        )}>
          {/* Lane A */}
          <LaneContainer lane="A">
            {result.lane_a?.responses?.map((resp, idx) => (
              <AgentCardV2
                key={idx}
                role={resp.role as "empiricist" | "skeptic" | "mechanist" | "speculator" | "pragmatist" | "patient_voice" | "arbitrator" | "advocate"}
                model={resp.model}
                content={resp.content}
                confidence={resp.confidence}
                state="complete"
                lane="A"
              />
            ))}
          </LaneContainer>
          
          {/* Lane B - only show if it has responses */}
          {result.lane_b?.responses?.length ? (
            <LaneContainer lane="B">
              {result.lane_b.responses.map((resp, idx) => (
                <AgentCardV2
                  key={idx}
                  role={resp.role as "empiricist" | "skeptic" | "mechanist" | "speculator" | "pragmatist" | "patient_voice" | "arbitrator" | "advocate"}
                  model={resp.model}
                  content={resp.content}
                  confidence={resp.confidence}
                  state="complete"
                  lane="B"
                />
              ))}
            </LaneContainer>
          ) : result.routing?.mode === "STANDARD_CARE" && (
            <div className="hidden lg:flex items-center justify-center p-8 rounded-xl border border-dashed border-slate-700/50 bg-slate-800/20">
              <div className="text-center">
                <span className="text-4xl mb-3 block opacity-50">🟣</span>
                <p className="text-sm text-slate-500">Exploratory lane not activated</p>
                <p className="text-xs text-slate-600 mt-1">Standard Care mode uses only clinical evidence</p>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Synthesis */}
      {result.synthesis && (
        <SynthesisView
          synthesis={{
            clinical_consensus: result.synthesis.clinical_consensus || {
              recommendation: "",
              evidence_basis: [],
              confidence: 0,
              safety_profile: "",
              contraindications: [],
            },
            exploratory_considerations: (result.synthesis.exploratory_considerations || []).map(ec => ({
              hypothesis: ec.hypothesis || "",
              mechanism: ec.mechanism || "",
              evidence_level: (ec.evidence_level || "theoretical") as "theoretical" | "preclinical" | "early_clinical" | "off_label",
              potential_benefit: ec.potential_benefit || "",
              risks: ec.risks || [],
              what_would_validate: ec.what_would_validate || "",
            })),
            tensions: (result.synthesis.tensions || []).map(t => ({
              description: t.description || "",
              lane_a_position: t.lane_a_position || "",
              lane_b_position: t.lane_b_position || "",
              resolution: (t.resolution || "unresolved") as "defer_to_clinical" | "defer_to_exploration" | "unresolved" | "context_dependent",
            })),
            safety_concerns_raised: result.synthesis.safety_concerns || [],
            stagnation_concerns_raised: result.synthesis.stagnation_concerns || [],
            what_would_change_mind: result.synthesis.what_would_change || "",
            preserved_dissent: result.synthesis.preserved_dissent || [],
            overall_confidence: result.synthesis.overall_confidence || 0,
          }}
        />
      )}

      {/* Fragility Profile */}
      {result.fragility_results && result.fragility_results.length > 0 && (
        <FragilityProfile
          entries={result.fragility_results.map(f => ({
            perturbation: f.perturbation || "",
            survives: f.survives ?? true,
            modification: f.modification,
            alternativeRecommendation: f.alternative_recommendation,
          }))}
        />
      )}
      
      {/* Meta info */}
      <div className="flex items-center justify-between text-sm text-slate-500 pt-4 border-t border-slate-700/50">
        <div className="flex items-center gap-4">
          <span>Mode: {result.mode}</span>
          {result.total_tokens && (
            <span>{result.total_tokens.toLocaleString()} tokens</span>
          )}
          {result.total_cost && (
            <span>${result.total_cost.toFixed(4)}</span>
          )}
        </div>
        {result.duration_ms && (
          <span>{(result.duration_ms / 1000).toFixed(1)}s</span>
        )}
      </div>
    </motion.div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function Home() {
  // Version state
  const [conferenceVersion, setConferenceVersion] = useState<ConferenceVersion>("v1");
  const enableV2 = conferenceVersion === "v2.1";

  // Config state
  const [config, setConfig] = useState<ConferenceConfig>(DEFAULT_CONFIG);
  const [v21Config, setV21Config] = useState<V21Config>(DEFAULT_V21_CONFIG);

  // v2.1 specific state
  const [patientContext, setPatientContext] = useState<PatientContext>({});
  const [v2Result, setV2Result] = useState<V2ConferenceResult | null>(null);

  // Activity feed events
  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([]);

  // Current query for session saving
  const [currentQuery, setCurrentQuery] = useState<string>("");
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

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

  // Add activity event helper
  const addActivityEvent = useCallback((event: Omit<ActivityEvent, "timestamp">) => {
    setActivityEvents(prev => [...prev, { ...event, timestamp: new Date() }]);
  }, []);

  // Track last phase to avoid duplicate events
  const lastPhaseRef = useRef<string>("");
  
  // Watch conferenceState.phase and add activity events
  useEffect(() => {
    const { phase, status, progress } = conferenceState;
    
    // Skip if phase hasn't changed or is empty
    if (!phase || phase === lastPhaseRef.current) return;
    lastPhaseRef.current = phase;
    
    // Determine event type based on phase
    let eventType: ActivityEvent["type"] = "agent";
    if (phase.includes("Routing")) eventType = "routing";
    else if (phase.includes("Scout") || phase.includes("Literature")) eventType = "scout";
    else if (phase.includes("Lane A") || phase.includes("Lane B")) eventType = "agent";
    else if (phase.includes("Cross") || phase.includes("Feasibility")) eventType = "critique";
    else if (phase.includes("Synthes")) eventType = "synthesis";
    else if (phase.includes("Testing") || phase.includes("Fragility")) eventType = "fragility";
    else if (phase === "Complete") eventType = "complete";
    else if (status === "error") eventType = "error";
    
    addActivityEvent({
      type: eventType,
      phase,
      status: status === "complete" ? "complete" : status === "error" ? "error" : "running",
      details: { 
        message: phase,
        completedEvents: Math.round(progress),
        totalEvents: 100,
      },
    });
  }, [conferenceState.phase, conferenceState.status, conferenceState.progress, addActivityEvent]);

  // Handle conference start
  const handleStartConference = useCallback(
    async (query: string) => {
      setCurrentQuery(query);
      setActivityEvents([]);
      
      // Add start event
      addActivityEvent({
        type: "start",
        phase: "Conference Started",
        status: "complete",
        details: { message: `Starting ${enableV2 ? "v2.1" : "v1"} conference` },
      });

      // Build request
      const request = {
        query,
        agents: config.agents,
        arbitrator_model: config.arbitratorModel,
        num_rounds: config.numRounds,
        topology: config.topology,
        enable_grounding: config.enableGrounding,
        enable_fragility: enableV2 ? v21Config.enableFragilityTesting : config.enableFragility,
        fragility_tests: enableV2 ? v21Config.fragilityTests : config.fragilityTests,
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
        enable_scout: enableV2 ? v21Config.enableScout : false,
        enable_routing: enableV2,
        risk_tolerance: enableV2 ? v21Config.riskTolerance : undefined,
        mode_override: enableV2 && v21Config.modeOverride !== "auto" ? v21Config.modeOverride : undefined,
      };

      if (enableV2) {
        addActivityEvent({
          type: "routing",
          phase: "Intelligent Router",
          status: "running",
          details: { message: "Analyzing query complexity..." },
        });

        const result = await startV2Conference(request);
        if (result) {
          setV2Result(result as V2ConferenceResult);
          
          // Save session
          const sessionId = crypto.randomUUID();
          setCurrentSessionId(sessionId);
          await saveSession({
            id: sessionId,
            timestamp: new Date(),
            query,
            version: "v2.1",
            resultPreview: (result as V2ConferenceResult).synthesis?.clinical_consensus?.recommendation?.slice(0, 100) || "Conference completed",
            fullResult: result as V2ConferenceResult,
          });
        }
      } else {
        await startConference(request);
        
        // Save session after completion
        if (conferenceState.result) {
          const sessionId = crypto.randomUUID();
          setCurrentSessionId(sessionId);
          await saveSession({
            id: sessionId,
            timestamp: new Date(),
            query,
            version: "v1",
            resultPreview: conferenceState.result.synthesis?.recommendation?.slice(0, 100) || "Conference completed",
            fullResult: conferenceState.result,
          });
        }
      }
    },
    [config, v21Config, files, enableV2, patientContext, startConference, startV2Conference, addActivityEvent, conferenceState.result]
  );

  // Handle loading a session from history
  const handleLoadSession = useCallback((session: StoredSession) => {
    setCurrentSessionId(session.id);
    setCurrentQuery(session.query);
    setConferenceVersion(session.version);
    
    if (session.version === "v2.1") {
      setV2Result(session.fullResult as V2ConferenceResult);
    }
    // For v1, we'd need to set conferenceState.result which is managed by the hook
  }, []);

  // Handle reset
  const handleReset = useCallback(() => {
    stopConference();
    setFiles([]);
    setV2Result(null);
    setPatientContext({});
    setActivityEvents([]);
    setCurrentQuery("");
    setCurrentSessionId(null);
  }, [stopConference]);

  const isRunning = conferenceState.status === "running" || conferenceState.status === "starting";
  const isComplete = conferenceState.status === "complete" || (enableV2 && v2Result !== null);
  const hasError = conferenceState.status === "error";

  return (
    <div className="min-h-screen bg-[#0a0f1a]">
      {/* Ambient glow effects */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-cyan-500/5 rounded-full blur-[150px]" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-violet-500/5 rounded-full blur-[150px]" />
      </div>

      {/* Header */}
      <Header
        isConnected={isConnected}
        conferenceStatus={conferenceState.status === "starting" ? "running" : conferenceState.status}
      />

      {/* Main content */}
      <main className="relative max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-12 gap-6">
          {/* Left column - Config & History */}
          <aside className="col-span-4">
            <div className="sticky top-24 space-y-4">
              {/* Version Toggle - Prominent placement */}
              <Card className="bg-slate-800/40 border-slate-700/50 backdrop-blur-sm">
                <CardContent className="py-4">
                  <div className="flex flex-col items-center">
                    <VersionToggle
                      version={conferenceVersion}
                      onVersionChange={setConferenceVersion}
                      disabled={isRunning}
                      showDescription={true}
                      size="lg"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Config Panel */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-xs font-medium text-slate-500 uppercase tracking-wider flex items-center gap-2">
                    <Terminal className="w-3.5 h-3.5" />
                    Configuration
                  </h2>
                  {(isComplete || hasError) && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleReset}
                      className="text-xs"
                    >
                      <RefreshCw className="w-3 h-3 mr-1.5" />
                      New
                    </Button>
                  )}
                </div>
                
                {enableV2 ? (
                  <ConfigPanelV21
                    config={v21Config}
                    onChange={setV21Config}
                    disabled={isRunning}
                  />
                ) : (
                  <ConfigPanel
                    config={config}
                    onChange={setConfig}
                    disabled={isRunning}
                  />
                )}
              </div>

              {/* Session History */}
              <SessionHistoryPanel
                onLoadSession={handleLoadSession}
                currentSessionId={currentSessionId}
              />
            </div>
          </aside>

          {/* Center column - Main content */}
          <div className="col-span-8 space-y-6">
            {/* Query input section */}
            {!isRunning && !isComplete && !hasError && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
              >
                <Card className="bg-slate-800/40 border-slate-700/50 backdrop-blur-sm overflow-hidden">
                  {/* Card header with gradient accent */}
                  <div className={cn(
                    "h-1",
                    enableV2 
                      ? "bg-gradient-to-r from-violet-500 via-cyan-500 to-violet-500"
                      : "bg-gradient-to-r from-cyan-500 to-blue-500"
                  )} />
                  
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "p-2.5 rounded-lg border",
                        enableV2
                          ? "bg-gradient-to-br from-violet-500/20 to-cyan-500/20 border-cyan-500/30"
                          : "bg-cyan-500/10 border-cyan-500/30"
                      )}>
                        {enableV2 ? (
                          <GitBranch className="w-5 h-5 text-cyan-400" />
                        ) : (
                          <Zap className="w-5 h-5 text-cyan-400" />
                        )}
                      </div>
                      <div>
                        <CardTitle className="flex items-center gap-2">
                          Clinical Scenario
                          <VersionBadge version={conferenceVersion} />
                        </CardTitle>
                        <p className="text-sm text-slate-500 mt-1">
                          {enableV2 
                            ? "Two-lane adversarial deliberation with live literature search"
                            : "Multi-agent deliberation with structured rounds"
                          }
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
                    <div className="pt-4 border-t border-slate-700/50">
                      <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                        <FileText className="w-4 h-4 text-slate-400" />
                        Case Documents
                        <span className="text-xs text-slate-500 font-normal">(optional)</span>
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

                    {/* Patient Context (v2.1 only) */}
                    <AnimatePresence>
                      {enableV2 && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          className="pt-4 border-t border-slate-700/50"
                        >
                          <PatientContextForm
                            value={patientContext}
                            onChange={setPatientContext}
                          />
                        </motion.div>
                      )}
                    </AnimatePresence>
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
                <Card className="bg-slate-800/40 border-slate-700/50 backdrop-blur-sm overflow-hidden">
                  <div className="h-1 bg-gradient-to-r from-cyan-500 via-violet-500 to-cyan-500 animate-pulse" />
                  <CardContent className="py-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="relative">
                          <div className="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center">
                            <Activity className="w-5 h-5 text-cyan-400 animate-pulse" />
                          </div>
                          <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-cyan-500 animate-ping" />
                        </div>
                        <div>
                          <h3 className="text-sm font-medium text-slate-200">
                            {enableV2 ? "v2.1 Conference Running" : "Conference Running"}
                          </h3>
                          <MiniTimeline
                            currentRound={conferenceState.currentRound}
                            totalRounds={conferenceState.totalRounds}
                            phase={conferenceState.phase}
                          />
                        </div>
                      </div>

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

                {/* Activity Feed */}
                {activityEvents.length > 0 && (
                  <ActivityFeed events={activityEvents} />
                )}

                {/* Agent grid */}
                <div>
                  <h3 className="text-sm font-medium text-slate-400 mb-4 flex items-center gap-2">
                    <Layers className="w-4 h-4" />
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
                <Card className="border-red-500/30 bg-red-500/5 backdrop-blur-sm">
                  <CardContent className="py-6">
                    <div className="flex items-center gap-4">
                      <div className="p-3 rounded-full bg-red-500/10">
                        <Activity className="w-6 h-6 text-red-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-medium text-red-400">
                          Conference Error
                        </h3>
                        <p className="text-sm text-slate-400 mt-1">
                          {conferenceState.error}
                        </p>
                      </div>
                      <Button
                        variant="outline"
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
            {isComplete && !isRunning && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                {enableV2 && v2Result ? (
                  <V2ResultsDisplay result={v2Result} />
                ) : conferenceState.result && (
                  <Results result={conferenceState.result} />
                )}
              </motion.div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative border-t border-slate-800/50 mt-16">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between text-xs text-slate-600">
            <p className="flex items-center gap-2">
              <Sparkles className="w-3 h-3" />
              AI Case Conference System
            </p>
            <p>
              Powered by{" "}
              <a
                href="https://openrouter.ai"
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyan-500 hover:text-cyan-400 transition-colors"
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
