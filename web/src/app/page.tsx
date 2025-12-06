"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  RefreshCw,
  Activity,
  FileText,
  Terminal,
  GitBranch,
  Brain,
  Sparkles,
  Square,
  Layers,
} from "lucide-react";

import { Header } from "@/components/conference/Header";
import { QueryInput, FileUpload } from "@/components/conference/QueryInput";
import { ConfigPanel, DEFAULT_CONFIG, type ConferenceConfig } from "@/components/conference/ConfigPanel";
import { PatientContextForm } from "@/components/conference/PatientContextForm";
import { SessionHistoryPanel } from "@/components/conference/SessionHistoryPanel";
import { LearningDashboard } from "@/components/conference/LearningDashboard";
import { V2ResultsDisplay } from "@/components/conference/V2ResultsDisplay";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useConference } from "@/hooks/useConference";
import { apiClient, type PatientContext, type V2ConferenceResult } from "@/lib/api";
import { saveSession, type ConferenceSession } from "@/lib/sessionStorage";
import { cn } from "@/lib/utils";

// Conference Components
import { AgentCardV2, type AgentRole } from "@/components/conference/v2";

// Activity Feed and Progress for real-time feedback
import { ActivityFeed, type ActivityEvent } from "@/components/conference/feedback/ActivityFeed";
import { MasterProgressBar } from "@/components/conference/feedback/MasterProgressBar";


// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function Home() {
  // Config state
  const [config, setConfig] = useState<ConferenceConfig>(DEFAULT_CONFIG);

  // Patient context for routing
  const [patientContext, setPatientContext] = useState<PatientContext>({});
  
  // Conference result
  const [result, setResult] = useState<V2ConferenceResult | null>(null);

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
  const { state: conferenceState, startConference, stopConference } = useConference();

  // Check API connection on mount
  useEffect(() => {
    apiClient.healthCheck().then(setIsConnected);
  }, []);

  // Counter for unique event IDs
  const eventIdRef = useRef(0);
  
  // Add activity event helper
  const addActivityEvent = useCallback((event: Omit<ActivityEvent, "timestamp" | "id">) => {
    eventIdRef.current += 1;
    setActivityEvents(prev => [...prev, { 
      ...event, 
      id: `event-${eventIdRef.current}-${Date.now()}`,
      timestamp: new Date() 
    }]);
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
        details: { message: "Starting conference" },
      });

      // Build request - use agents from config
      const enabledAgents = config.agents
        .filter(a => a.enabled)
        .map(a => ({ role: a.role, model: a.model }));
      
      const request = {
        query,
        agents: enabledAgents,
        arbitrator_model: "anthropic/claude-sonnet-4",
        enable_grounding: true,
        enable_fragility: config.enableFragilityTesting,
        fragility_tests: config.fragilityTests,
        fragility_model: "anthropic/claude-sonnet-4",
        librarian: files.length > 0
          ? {
              model: config.librarian.model,
              max_queries_per_turn: config.librarian.maxQueriesPerTurn,
            }
          : undefined,
        // Patient context for routing
        patient_context: patientContext,
        // Conference options
        enable_scout: config.enableScout,
        enable_routing: true,
        enable_learning: config.enableLearning,
        // Overrides (only if not auto)
        mode_override: config.modeOverride !== "auto" ? config.modeOverride : undefined,
        topology_override: config.topologyOverride !== "auto" ? config.topologyOverride : undefined,
        // Model configuration
        model_config_v3: config.modelConfig,
      };

      addActivityEvent({
        type: "routing",
        phase: "Intelligent Router",
        status: "running",
        details: { message: "Analyzing query complexity..." },
      });

      const conferenceResult = await startConference(request);
      if (conferenceResult) {
        setResult(conferenceResult as V2ConferenceResult);
        
        // Save session
        const sessionId = crypto.randomUUID();
        setCurrentSessionId(sessionId);
        await saveSession({
          id: sessionId,
          timestamp: new Date(),
          query,
          mode: (conferenceResult as V2ConferenceResult).mode,
          agentCount: (conferenceResult as V2ConferenceResult).routing?.active_agents?.length || 0,
          status: "complete",
          duration: (conferenceResult as V2ConferenceResult).duration_ms,
          tokensUsed: (conferenceResult as V2ConferenceResult).total_tokens,
          cost: (conferenceResult as V2ConferenceResult).total_cost,
          result: conferenceResult,
          summary: (conferenceResult as V2ConferenceResult).synthesis?.clinical_consensus?.recommendation?.slice(0, 100) || "Conference completed",
          patientContext: patientContext,
        });
      }
    },
    [config, files, patientContext, startConference, addActivityEvent]
  );

  // Handle loading a session from history
  const handleLoadSession = useCallback((session: ConferenceSession) => {
    setCurrentSessionId(session.id);
    setCurrentQuery(session.query);
    setResult(session.result as V2ConferenceResult);
  }, []);

  // Handle reset
  const handleReset = useCallback(() => {
    stopConference();
    setFiles([]);
    setResult(null);
    setPatientContext({});
    setActivityEvents([]);
    setCurrentQuery("");
    setCurrentSessionId(null);
  }, [stopConference]);

  const isRunning = conferenceState.status === "running" || conferenceState.status === "starting";
  const isComplete = conferenceState.status === "complete" || result !== null;
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
                
                <ConfigPanel
                  config={config}
                  onChange={setConfig}
                  disabled={isRunning}
                  hasFiles={files.length > 0}
                />
              </div>

              {/* Learning Dashboard */}
              <LearningDashboard />

              {/* Session History */}
              <SessionHistoryPanel
                onSelectSession={handleLoadSession}
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
                    config.enableLearning 
                      ? "bg-gradient-to-r from-purple-500 via-cyan-500 to-purple-500"
                      : "bg-gradient-to-r from-cyan-500 via-emerald-500 to-cyan-500"
                  )} />
                  
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "p-2.5 rounded-lg border",
                        config.enableLearning
                          ? "bg-gradient-to-br from-purple-500/20 to-cyan-500/20 border-purple-500/30"
                          : "bg-gradient-to-br from-cyan-500/20 to-emerald-500/20 border-cyan-500/30"
                      )}>
                        {config.enableLearning ? (
                          <Brain className="w-5 h-5 text-purple-400" />
                        ) : (
                          <GitBranch className="w-5 h-5 text-cyan-400" />
                        )}
                      </div>
                      <div>
                        <CardTitle className="flex items-center gap-2">
                          Clinical Case Conference
                          <Badge className={cn(
                            "text-[10px]",
                            config.enableLearning 
                              ? "bg-purple-500/20 text-purple-300 border-purple-500/30"
                              : "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
                          )}>
                            {config.enableLearning ? "Learning" : "Fresh"}
                          </Badge>
                        </CardTitle>
                        <p className="text-sm text-slate-500 mt-1">
                          Two-lane adversarial deliberation with live literature search
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

                    {/* Patient Context */}
                    <div className="pt-4 border-t border-slate-700/50">
                      <PatientContextForm
                        value={patientContext}
                        onChange={setPatientContext}
                      />
                    </div>
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
                            Conference Running
                          </h3>
                          <p className="text-xs text-slate-400">
                            {conferenceState.phase || "Initializing..."}
                          </p>
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

                    <MasterProgressBar
                      phases={[
                        { key: "routing", label: "Routing", status: conferenceState.progress >= 10 ? "complete" : conferenceState.progress > 0 ? "running" : "pending" },
                        { key: "scout", label: "Scout", status: conferenceState.progress >= 25 ? "complete" : conferenceState.progress >= 10 ? "running" : "pending" },
                        { key: "lane_a", label: "Lane A", status: conferenceState.progress >= 50 ? "complete" : conferenceState.progress >= 25 ? "running" : "pending" },
                        { key: "lane_b", label: "Lane B", status: conferenceState.progress >= 70 ? "complete" : conferenceState.progress >= 50 ? "running" : "pending" },
                        { key: "cross_exam", label: "Cross-Exam", status: conferenceState.progress >= 85 ? "complete" : conferenceState.progress >= 70 ? "running" : "pending" },
                        { key: "synthesis", label: "Synthesis", status: conferenceState.progress >= 100 ? "complete" : conferenceState.progress >= 85 ? "running" : "pending" },
                      ]}
                      currentPhase={conferenceState.phase}
                      overallProgress={conferenceState.progress}
                      isComplete={conferenceState.status === "complete"}
                      error={conferenceState.error || undefined}
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
                      <AgentCardV2
                        key={agent.role}
                        role={agent.role as AgentRole}
                        model={agent.model}
                        lane="A"
                        state={agent.status === "thinking" ? "streaming" : agent.status === "complete" ? "complete" : "waiting"}
                        confidence={agent.confidence ?? undefined}
                        content={agent.content?.substring(0, 200)}
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
            {isComplete && !isRunning && result && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <V2ResultsDisplay result={result} />
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
