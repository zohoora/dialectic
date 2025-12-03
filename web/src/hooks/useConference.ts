"use client";

import { useState, useCallback, useRef } from "react";
import { apiClient, StreamEvent, ConferenceRequest, AgentResponse, ConferenceResult } from "@/lib/api";

export type AgentStatus = "idle" | "thinking" | "responding" | "complete";

export interface AgentState {
  role: string;
  model: string;
  status: AgentStatus;
  content: string;
  confidence: number | null;
  changed: boolean;
}

export interface ConferenceState {
  status: "idle" | "starting" | "running" | "complete" | "error";
  conferenceId: string | null;
  currentRound: number;
  totalRounds: number;
  phase: string;
  agents: Record<string, AgentState>;
  rounds: Array<{
    round_number: number;
    responses: AgentResponse[];
  }>;
  result: ConferenceResult | null;
  error: string | null;
  progress: number;
}

const initialState: ConferenceState = {
  status: "idle",
  conferenceId: null,
  currentRound: 0,
  totalRounds: 0,
  phase: "",
  agents: {},
  rounds: [],
  result: null,
  error: null,
  progress: 0,
};

export function useConference() {
  const [state, setState] = useState<ConferenceState>(initialState);
  const cleanupRef = useRef<(() => void) | null>(null);

  const updateState = useCallback((updates: Partial<ConferenceState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  const updateAgent = useCallback((role: string, updates: Partial<AgentState>) => {
    setState((prev) => ({
      ...prev,
      agents: {
        ...prev.agents,
        [role]: { ...prev.agents[role], ...updates },
      },
    }));
  }, []);

  const handleEvent = useCallback((event: StreamEvent) => {
    const { event: eventType, data } = event;

    switch (eventType) {
      case "conference_start":
        updateState({
          conferenceId: data.conference_id as string,
          totalRounds: data.num_rounds as number,
          phase: "Starting",
          progress: 5,
        });
        break;

      case "librarian_start":
        updateState({ phase: "Analyzing Documents", progress: 8 });
        break;

      case "librarian_complete":
        updateState({ phase: "Documents Analyzed", progress: 10 });
        break;

      case "round_start":
        const roundNum = data.round_number as number;
        const totalRounds = data.total_rounds as number;
        updateState({
          currentRound: roundNum,
          totalRounds,
          phase: `Round ${roundNum}`,
          progress: 10 + ((roundNum - 1) / totalRounds) * 60,
        });
        // Reset agent states for new round
        setState((prev) => {
          const resetAgents = { ...prev.agents };
          Object.keys(resetAgents).forEach((role) => {
            resetAgents[role] = {
              ...resetAgents[role],
              status: "idle",
              content: "",
              confidence: null,
              changed: false,
            };
          });
          return { ...prev, agents: resetAgents };
        });
        break;

      case "agent_thinking":
        const thinkingRole = data.role as string;
        updateAgent(thinkingRole, { status: "thinking" });
        break;

      case "agent_token":
        const tokenRole = data.role as string;
        const token = data.token as string;
        setState((prev) => ({
          ...prev,
          agents: {
            ...prev.agents,
            [tokenRole]: {
              ...prev.agents[tokenRole],
              status: "responding",
              content: (prev.agents[tokenRole]?.content || "") + token,
            },
          },
        }));
        break;

      case "agent_complete":
        const completeRole = data.role as string;
        updateAgent(completeRole, {
          status: "complete",
          content: data.content as string,
          confidence: data.confidence as number,
          changed: data.changed as boolean,
        });
        break;

      case "round_complete":
        const completedRound = data.round_number as number;
        setState((prev) => {
          const roundResponses: AgentResponse[] = Object.values(prev.agents).map((agent) => ({
            role: agent.role,
            model: agent.model,
            content: agent.content,
            confidence: agent.confidence || 0,
            changed_from_previous: agent.changed,
          }));
          return {
            ...prev,
            rounds: [
              ...prev.rounds,
              { round_number: completedRound, responses: roundResponses },
            ],
            progress: 10 + (completedRound / prev.totalRounds) * 60,
          };
        });
        break;

      case "grounding_start":
        updateState({ phase: "Verifying Citations", progress: 75 });
        break;

      case "grounding_complete":
        updateState({ phase: "Citations Verified", progress: 80 });
        break;

      case "arbitration_start":
        updateState({ phase: "Synthesizing", progress: 82 });
        break;

      case "arbitration_complete":
        updateState({ phase: "Synthesis Complete", progress: 88 });
        break;

      case "fragility_start":
        updateState({ phase: "Stress Testing", progress: 90 });
        break;

      case "fragility_test":
        const testNum = data.test_number as number;
        const totalTests = data.total_tests as number;
        updateState({
          phase: `Testing ${testNum}/${totalTests}`,
          progress: 90 + (testNum / totalTests) * 8,
        });
        break;

      case "fragility_complete":
        updateState({ phase: "Testing Complete", progress: 98 });
        break;

      case "conference_complete":
        updateState({
          status: "complete",
          phase: "Complete",
          progress: 100,
          result: data as unknown as ConferenceResult,
        });
        break;

      case "error":
        updateState({
          status: "error",
          error: data.message as string,
        });
        break;
    }
  }, [updateState, updateAgent]);

  const startConference = useCallback(
    async (request: ConferenceRequest) => {
      // Reset state
      setState({
        ...initialState,
        status: "starting",
        agents: request.agents.reduce(
          (acc, agent) => ({
            ...acc,
            [agent.role]: {
              role: agent.role,
              model: agent.model,
              status: "idle" as AgentStatus,
              content: "",
              confidence: null,
              changed: false,
            },
          }),
          {}
        ),
      });

      try {
        // Start conference and get stream URL
        const { conference_id } = await apiClient.startConference(request);

        updateState({ status: "running", conferenceId: conference_id });

        // Start streaming
        cleanupRef.current = apiClient.streamConference(
          conference_id,
          handleEvent,
          (error) => {
            updateState({ status: "error", error: error.message });
          },
          () => {
            // Streaming complete
          }
        );
      } catch (error) {
        updateState({
          status: "error",
          error: error instanceof Error ? error.message : "Failed to start conference",
        });
      }
    },
    [handleEvent, updateState]
  );

  const stopConference = useCallback(() => {
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
    setState(initialState);
  }, []);

  return {
    state,
    startConference,
    stopConference,
  };
}

