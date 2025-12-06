"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { V2ConferenceResult } from "@/lib/api";

// Conference Components
import {
  RoutingDecisionBar,
  ScoutFindingsPanel,
  LaneContainer,
  AgentCardV2,
  SynthesisView,
  FragilityProfile,
} from "@/components/conference/v2";

interface V2ResultsDisplayProps {
  result: V2ConferenceResult;
}

export function V2ResultsDisplay({ result }: V2ResultsDisplayProps) {
  if (!result) {
    return <div className="text-red-500">Result is null!</div>;
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
      {result.fragility_report && result.fragility_report.results.length > 0 && (
        <FragilityProfile
          entries={result.fragility_report.results.map(f => ({
            perturbation: f.perturbation,
            description: f.explanation,
            result: f.outcome === "survives" ? "holds" : f.outcome === "modifies" ? "modified" : "changes",
            alternativeRecommendation: f.modified_recommendation,
          }))}
        />
      )}
      
      {/* Meta info */}
      <ResultsMetaInfo result={result} />
    </motion.div>
  );
}

function ResultsMetaInfo({ result }: { result: V2ConferenceResult }) {
  return (
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
  );
}

