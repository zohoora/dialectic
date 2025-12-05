"use client";

import { motion } from "framer-motion";
import {
  CheckCircle,
  AlertTriangle,
  Lightbulb,
  Scale,
  Shield,
  Beaker,
  ChevronDown,
  ChevronUp,
  FileText,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type {
  V2ConferenceResult,
  ClinicalConsensus,
  ExploratoryConsideration,
  Tension,
  ScoutReport,
  LaneResult,
  AgentResponse,
} from "@/lib/api";

interface TwoLaneResultsProps {
  result: V2ConferenceResult;
}

// =============================================================================
// SCOUT FINDINGS SECTION
// =============================================================================

function ScoutFindings({ report }: { report: ScoutReport }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (report.is_empty) {
    return (
      <Card className="bg-slate-800/30 border-slate-700/50">
        <CardHeader className="py-3 px-4">
          <div className="flex items-center gap-2 text-slate-400">
            <FileText className="w-4 h-4" />
            <span className="text-sm">Scout found no recent relevant literature</span>
          </div>
        </CardHeader>
      </Card>
    );
  }

  const totalCitations =
    report.meta_analyses.length +
    report.high_quality_rcts.length +
    report.preliminary_evidence.length +
    report.conflicting_evidence.length;

  return (
    <Card className="bg-indigo-900/20 border-indigo-500/30">
      <CardHeader
        className="py-3 px-4 cursor-pointer hover:bg-indigo-900/30 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-500/20">
              <FileText className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h3 className="font-medium text-indigo-300">Scout Literature Search</h3>
              <p className="text-xs text-slate-400">
                {totalCitations} citations • Keywords: {report.query_keywords.join(", ")}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {report.meta_analyses.length > 0 && (
              <Badge className="bg-purple-500/20 text-purple-300">
                {report.meta_analyses.length} Meta
              </Badge>
            )}
            {report.high_quality_rcts.length > 0 && (
              <Badge className="bg-green-500/20 text-green-300">
                {report.high_quality_rcts.length} RCT
              </Badge>
            )}
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="pt-0 space-y-4">
          {report.meta_analyses.length > 0 && (
            <CitationList
              title="Meta-Analyses"
              citations={report.meta_analyses}
              colorClass="purple"
            />
          )}
          {report.high_quality_rcts.length > 0 && (
            <CitationList
              title="Randomized Controlled Trials"
              citations={report.high_quality_rcts}
              colorClass="green"
            />
          )}
          {report.preliminary_evidence.length > 0 && (
            <CitationList
              title="Preliminary Evidence"
              citations={report.preliminary_evidence}
              colorClass="yellow"
            />
          )}
          {report.conflicting_evidence.length > 0 && (
            <CitationList
              title="Conflicting Evidence"
              citations={report.conflicting_evidence}
              colorClass="red"
            />
          )}
        </CardContent>
      )}
    </Card>
  );
}

function CitationList({
  title,
  citations,
  colorClass,
}: {
  title: string;
  citations: ScoutReport["meta_analyses"];
  colorClass: string;
}) {
  const colorMap: Record<string, string> = {
    purple: "border-purple-500/30 bg-purple-500/10",
    green: "border-green-500/30 bg-green-500/10",
    yellow: "border-yellow-500/30 bg-yellow-500/10",
    red: "border-red-500/30 bg-red-500/10",
  };

  return (
    <div>
      <h4 className="text-sm font-medium text-slate-300 mb-2">{title}</h4>
      <div className="space-y-2">
        {citations.map((citation, idx) => (
          <div
            key={idx}
            className={cn("p-3 rounded-lg border", colorMap[colorClass])}
          >
            <p className="text-sm text-slate-200">{citation.title}</p>
            <p className="text-xs text-slate-400 mt-1">
              {citation.journal} • {citation.year}
              {citation.pmid && ` • PMID: ${citation.pmid}`}
            </p>
            {citation.key_finding && (
              <p className="text-xs text-slate-300 mt-2 italic">
                "{citation.key_finding}"
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// LANE A - CLINICAL CONSENSUS
// =============================================================================

function ClinicalConsensusCard({ consensus }: { consensus: ClinicalConsensus }) {
  return (
    <Card className="bg-emerald-900/20 border-emerald-500/30">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/20">
            <CheckCircle className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h3 className="font-semibold text-emerald-300">Clinical Consensus</h3>
            <p className="text-xs text-slate-400">Lane A • Evidence-Based</p>
          </div>
          <Badge
            className={cn(
              "ml-auto",
              consensus.confidence >= 0.7
                ? "bg-emerald-500/20 text-emerald-300"
                : consensus.confidence >= 0.4
                ? "bg-yellow-500/20 text-yellow-300"
                : "bg-red-500/20 text-red-300"
            )}
          >
            {Math.round(consensus.confidence * 100)}% Confidence
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Main Recommendation */}
        <div className="p-4 rounded-lg bg-emerald-950/50 border border-emerald-500/20">
          <h4 className="text-xs uppercase tracking-wider text-emerald-400 mb-2">
            Recommendation
          </h4>
          <div className="prose prose-sm prose-invert max-w-none">
            <ReactMarkdown>{consensus.recommendation}</ReactMarkdown>
          </div>
        </div>

        {/* Evidence Basis */}
        {consensus.evidence_basis.length > 0 && (
          <div>
            <h4 className="text-xs uppercase tracking-wider text-slate-400 mb-2">
              Evidence Basis
            </h4>
            <ul className="space-y-1">
              {consensus.evidence_basis.map((evidence, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-emerald-400 mt-1">•</span>
                  {evidence}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Safety Profile */}
        {consensus.safety_profile && (
          <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-4 h-4 text-yellow-400" />
              <h4 className="text-sm font-medium text-slate-300">Safety Profile</h4>
            </div>
            <p className="text-sm text-slate-400">{consensus.safety_profile}</p>
          </div>
        )}

        {/* Contraindications */}
        {consensus.contraindications.length > 0 && (
          <div className="p-3 rounded-lg bg-red-900/20 border border-red-500/30">
            <h4 className="text-xs uppercase tracking-wider text-red-400 mb-2">
              Contraindications
            </h4>
            <ul className="space-y-1">
              {consensus.contraindications.map((ci, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-red-300">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  {ci}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// LANE B - EXPLORATORY CONSIDERATIONS
// =============================================================================

function ExploratoryCard({
  considerations,
}: {
  considerations: ExploratoryConsideration[];
}) {
  if (considerations.length === 0) {
    return null;
  }

  return (
    <Card className="bg-violet-900/20 border-violet-500/30">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-violet-500/20">
            <Lightbulb className="w-5 h-5 text-violet-400" />
          </div>
          <div>
            <h3 className="font-semibold text-violet-300">Exploratory Considerations</h3>
            <p className="text-xs text-slate-400">Lane B • Hypotheses & Novel Approaches</p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {considerations.map((consideration, idx) => (
          <div
            key={idx}
            className="p-4 rounded-lg bg-violet-950/50 border border-violet-500/20"
          >
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-medium text-violet-300">
                <Beaker className="w-4 h-4 inline mr-2" />
                {consideration.hypothesis}
              </h4>
              <Badge className="bg-violet-500/20 text-violet-300">
                {consideration.evidence_level}
              </Badge>
            </div>

            {consideration.mechanism && (
              <p className="text-sm text-slate-300 mb-2">
                <span className="text-violet-400">Mechanism:</span>{" "}
                {consideration.mechanism}
              </p>
            )}

            {consideration.potential_benefit && (
              <p className="text-sm text-slate-300 mb-2">
                <span className="text-emerald-400">Potential benefit:</span>{" "}
                {consideration.potential_benefit}
              </p>
            )}

            {consideration.risks.length > 0 && (
              <div className="text-sm text-slate-300 mb-2">
                <span className="text-red-400">Risks:</span>{" "}
                {consideration.risks.join(", ")}
              </div>
            )}

            {consideration.what_would_validate && (
              <div className="mt-2 p-2 rounded bg-slate-800/50 text-xs text-slate-400">
                <TrendingUp className="w-3 h-3 inline mr-1 text-violet-400" />
                <span className="text-violet-400">Would validate:</span>{" "}
                {consideration.what_would_validate}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// TENSIONS SECTION
// =============================================================================

function TensionsCard({ tensions }: { tensions: Tension[] }) {
  if (tensions.length === 0) {
    return null;
  }

  return (
    <Card className="bg-amber-900/20 border-amber-500/30">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-500/20">
            <Scale className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h3 className="font-semibold text-amber-300">Tensions & Trade-offs</h3>
            <p className="text-xs text-slate-400">Conflicts between lanes</p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {tensions.map((tension, idx) => (
          <div
            key={idx}
            className="p-3 rounded-lg bg-amber-950/50 border border-amber-500/20"
          >
            <p className="font-medium text-amber-300 mb-2">{tension.description}</p>

            <div className="grid grid-cols-2 gap-2 text-xs">
              {tension.lane_a_position && (
                <div className="p-2 rounded bg-emerald-900/20 border border-emerald-500/20">
                  <span className="text-emerald-400">Lane A:</span>
                  <p className="text-slate-300 mt-1">{tension.lane_a_position}</p>
                </div>
              )}
              {tension.lane_b_position && (
                <div className="p-2 rounded bg-violet-900/20 border border-violet-500/20">
                  <span className="text-violet-400">Lane B:</span>
                  <p className="text-slate-300 mt-1">{tension.lane_b_position}</p>
                </div>
              )}
            </div>

            <p className="text-xs text-slate-400 mt-2">
              Resolution: <span className="text-amber-300">{tension.resolution}</span>
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// LANE RESPONSES
// =============================================================================

function LaneResponses({
  lane,
  responses,
  colorClass,
}: {
  lane: "A" | "B";
  responses: AgentResponse[];
  colorClass: string;
}) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  const colorMap: Record<string, { bg: string; border: string; text: string }> = {
    emerald: {
      bg: "bg-emerald-900/10",
      border: "border-emerald-500/20",
      text: "text-emerald-400",
    },
    violet: {
      bg: "bg-violet-900/10",
      border: "border-violet-500/20",
      text: "text-violet-400",
    },
  };

  const colors = colorMap[colorClass];

  return (
    <div className="space-y-2">
      <h4 className={cn("text-sm font-medium", colors.text)}>
        Lane {lane} Agent Responses
      </h4>
      {responses.map((response, idx) => (
        <div
          key={idx}
          className={cn("rounded-lg border", colors.bg, colors.border)}
        >
          <div
            className="p-3 cursor-pointer hover:opacity-80"
            onClick={() =>
              setExpandedAgent(expandedAgent === response.role ? null : response.role)
            }
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge className={cn("capitalize", colors.bg, colors.text)}>
                  {response.role}
                </Badge>
                <span className="text-xs text-slate-500">{response.model}</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge className="bg-slate-700/50 text-slate-300">
                  {Math.round(response.confidence * 100)}%
                </Badge>
                {expandedAgent === response.role ? (
                  <ChevronUp className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                )}
              </div>
            </div>
          </div>

          {expandedAgent === response.role && (
            <div className="px-3 pb-3 pt-0">
              <div className="prose prose-sm prose-invert max-w-none">
                <ReactMarkdown>{response.content}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function TwoLaneResults({ result }: TwoLaneResultsProps) {
  // Safely access synthesis with defaults
  const synthesis = result.synthesis ?? {
    overall_confidence: 0,
    clinical_consensus: null,
    exploratory_considerations: [],
    tensions: [],
    preserved_dissent: [],
    what_would_change: null,
  };

  const overallConfidence = synthesis.overall_confidence ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">Conference Results</h2>
          <p className="text-sm text-slate-400">
            Mode: {result.mode ?? "Unknown"}
            {result.total_tokens != null && ` • ${result.total_tokens.toLocaleString()} tokens`}
            {result.total_cost != null && ` • $${result.total_cost.toFixed(4)}`}
          </p>
        </div>
        <Badge
          className={cn(
            overallConfidence >= 0.7
              ? "bg-emerald-500/20 text-emerald-300"
              : overallConfidence >= 0.4
              ? "bg-yellow-500/20 text-yellow-300"
              : "bg-red-500/20 text-red-300"
          )}
        >
          {Math.round(overallConfidence * 100)}% Overall Confidence
        </Badge>
      </div>

      {/* Scout Findings */}
      {result.scout_report && <ScoutFindings report={result.scout_report} />}

      {/* Two-Lane Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Lane A - Clinical */}
        <div className="space-y-4">
          {synthesis.clinical_consensus && (
            <ClinicalConsensusCard consensus={synthesis.clinical_consensus} />
          )}
          {result.lane_a?.responses && (
            <LaneResponses
              lane="A"
              responses={result.lane_a.responses}
              colorClass="emerald"
            />
          )}
        </div>

        {/* Lane B - Exploratory */}
        <div className="space-y-4">
          {synthesis.exploratory_considerations && synthesis.exploratory_considerations.length > 0 && (
            <ExploratoryCard considerations={synthesis.exploratory_considerations} />
          )}
          {result.lane_b?.responses && (
            <LaneResponses
              lane="B"
              responses={result.lane_b.responses}
              colorClass="violet"
            />
          )}
        </div>
      </div>

      {/* Tensions */}
      {synthesis.tensions && synthesis.tensions.length > 0 && (
        <TensionsCard tensions={synthesis.tensions} />
      )}

      {/* Preserved Dissent */}
      {synthesis.preserved_dissent && synthesis.preserved_dissent.length > 0 && (
        <Card className="bg-slate-800/30 border-slate-700/50">
          <CardHeader className="pb-2">
            <h3 className="font-medium text-slate-300">Preserved Dissent</h3>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {synthesis.preserved_dissent.map((dissent, idx) => (
                <li key={idx} className="text-sm text-slate-400">
                  • {dissent}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* What Would Change */}
      {synthesis.what_would_change && (
        <Card className="bg-slate-800/30 border-slate-700/50">
          <CardHeader className="pb-2">
            <h3 className="font-medium text-slate-300">What Would Change This?</h3>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-400">{synthesis.what_would_change}</p>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}

