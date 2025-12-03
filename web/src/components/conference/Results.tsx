"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  ChevronDown,
  FileText,
  Beaker,
  Quote,
  Shield,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CircularProgress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { formatDuration, formatTokens, formatCost } from "@/lib/utils";
import type { ConferenceResult, AgentResponse } from "@/lib/api";

interface ResultsProps {
  result: ConferenceResult;
}

export function Results({ result }: ResultsProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      {/* Synthesis - Hero card */}
      <SynthesisCard
        consensus={result.synthesis.final_consensus}
        confidence={result.synthesis.confidence}
        model={result.synthesis.model}
      />

      {/* Dissent */}
      {result.dissent.preserved.length > 0 && (
        <DissentCard
          preserved={result.dissent.preserved}
          rationale={result.dissent.rationale}
        />
      )}

      {/* Grounding Report */}
      {result.grounding_report && (
        <GroundingCard report={result.grounding_report} />
      )}

      {/* Fragility Report */}
      {result.fragility_report && (
        <FragilityCard report={result.fragility_report} />
      )}

      {/* Detailed Rounds */}
      <RoundsAccordion rounds={result.rounds} />

      {/* Metrics */}
      <MetricsCard
        tokens={result.total_tokens}
        cost={result.total_cost}
        duration={result.duration_ms}
        conferenceId={result.conference_id}
      />
    </motion.div>
  );
}

// Synthesis card
function SynthesisCard({
  consensus,
  confidence,
  model,
}: {
  consensus: string;
  confidence: number;
  model: string;
}) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(consensus);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card variant="glass" glow="cyan" className="relative overflow-hidden">
      {/* Glow effect */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-32 bg-gradient-radial from-accent-primary/20 to-transparent" />

      <CardHeader className="relative">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent-primary/20 border border-accent-primary/30">
              <CheckCircle2 className="w-5 h-5 text-accent-primary" />
            </div>
            <div>
              <CardTitle className="gradient-text">Final Synthesis</CardTitle>
              <p className="text-xs text-slate-500 mt-1">
                Arbitrated by {model.split("/").pop()}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <CircularProgress
              value={confidence * 100}
              size={50}
              strokeWidth={3}
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={copyToClipboard}
              className="text-slate-400 hover:text-slate-200"
            >
              {copied ? (
                <Check className="w-4 h-4 text-green-400" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="relative">
        <div className="prose prose-invert prose-sm max-w-none">
          <p className="text-slate-200 leading-relaxed whitespace-pre-wrap">
            {consensus}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// Dissent card
function DissentCard({
  preserved,
  rationale,
}: {
  preserved: string[];
  rationale: string;
}) {
  return (
    <Card variant="bordered" className="border-yellow-500/20">
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
          </div>
          <div>
            <CardTitle className="text-yellow-400">Preserved Dissent</CardTitle>
            <p className="text-xs text-slate-500 mt-1">
              Minority viewpoints worth considering
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="space-y-3">
          {preserved.map((dissent, i) => (
            <div
              key={i}
              className="flex gap-3 p-3 rounded-lg bg-yellow-500/5 border border-yellow-500/10"
            >
              <Quote className="w-4 h-4 text-yellow-500/50 shrink-0 mt-0.5" />
              <p className="text-sm text-slate-300">{dissent}</p>
            </div>
          ))}
        </div>

        {rationale && (
          <div className="pt-3 border-t border-white/5">
            <p className="text-xs text-slate-500 mb-1">Rationale</p>
            <p className="text-sm text-slate-400">{rationale}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Grounding card
function GroundingCard({ report }: { report: Record<string, unknown> }) {
  const citations = (report.citations as Array<Record<string, unknown>>) || [];
  const verified = citations.filter((c) => c.verified).length;
  const failed = citations.length - verified;

  return (
    <Card variant="bordered" className="border-blue-500/20">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/30">
              <FileText className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <CardTitle className="text-blue-400">Evidence Grounding</CardTitle>
              <p className="text-xs text-slate-500 mt-1">
                PubMed verification results
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge variant="success">{verified} verified</Badge>
            {failed > 0 && <Badge variant="danger">{failed} failed</Badge>}
          </div>
        </div>
      </CardHeader>

      {citations.length > 0 && (
        <CardContent>
          <div className="space-y-2">
            {citations.slice(0, 5).map((citation, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-center gap-3 p-2 rounded-lg text-sm",
                  citation.verified
                    ? "bg-green-500/5 text-green-400"
                    : "bg-red-500/5 text-red-400"
                )}
              >
                {citation.verified ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                )}
                <span className="truncate">{citation.text as string}</span>
              </div>
            ))}
            {citations.length > 5 && (
              <p className="text-xs text-slate-500 text-center pt-2">
                +{citations.length - 5} more citations
              </p>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

// Fragility card
function FragilityCard({ report }: { report: Record<string, unknown> }) {
  const tests = (report.tests as Array<Record<string, unknown>>) || [];
  const survives = tests.filter((t) => t.outcome === "SURVIVES").length;
  const modifies = tests.filter((t) => t.outcome === "MODIFIES").length;
  const collapses = tests.filter((t) => t.outcome === "COLLAPSES").length;

  return (
    <Card variant="bordered" className="border-purple-500/20">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/30">
              <Beaker className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <CardTitle className="text-purple-400">Fragility Testing</CardTitle>
              <p className="text-xs text-slate-500 mt-1">
                Stress test results
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="success">{survives} survives</Badge>
            <Badge variant="warning">{modifies} modifies</Badge>
            <Badge variant="danger">{collapses} collapses</Badge>
          </div>
        </div>
      </CardHeader>

      {tests.length > 0 && (
        <CardContent>
          <div className="space-y-2">
            {tests.map((test, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-center justify-between p-3 rounded-lg text-sm",
                  test.outcome === "SURVIVES" && "bg-green-500/5",
                  test.outcome === "MODIFIES" && "bg-yellow-500/5",
                  test.outcome === "COLLAPSES" && "bg-red-500/5"
                )}
              >
                <div className="flex items-center gap-3">
                  <Shield
                    className={cn(
                      "w-4 h-4",
                      test.outcome === "SURVIVES" && "text-green-400",
                      test.outcome === "MODIFIES" && "text-yellow-400",
                      test.outcome === "COLLAPSES" && "text-red-400"
                    )}
                  />
                  <span className="text-slate-300">
                    {test.perturbation as string}
                  </span>
                </div>
                <Badge
                  variant={
                    test.outcome === "SURVIVES"
                      ? "success"
                      : test.outcome === "MODIFIES"
                      ? "warning"
                      : "danger"
                  }
                >
                  {test.outcome as string}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

// Rounds accordion
function RoundsAccordion({
  rounds,
}: {
  rounds: Array<{ round_number: number; responses: AgentResponse[] }>;
}) {
  const [expandedRounds, setExpandedRounds] = useState<Set<number>>(new Set());

  const toggleRound = (round: number) => {
    const newExpanded = new Set(expandedRounds);
    if (newExpanded.has(round)) {
      newExpanded.delete(round);
    } else {
      newExpanded.add(round);
    }
    setExpandedRounds(newExpanded);
  };

  return (
    <Card variant="bordered">
      <CardHeader>
        <CardTitle>Deliberation Details</CardTitle>
      </CardHeader>

      <CardContent className="space-y-2">
        {rounds.map((round) => (
          <div
            key={round.round_number}
            className="border border-white/5 rounded-lg overflow-hidden"
          >
            <button
              onClick={() => toggleRound(round.round_number)}
              className="w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors"
            >
              <span className="text-sm font-medium text-slate-200">
                Round {round.round_number}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">
                  {round.responses.length} responses
                </span>
                <ChevronDown
                  className={cn(
                    "w-4 h-4 text-slate-400 transition-transform",
                    expandedRounds.has(round.round_number) && "rotate-180"
                  )}
                />
              </div>
            </button>

            {expandedRounds.has(round.round_number) && (
              <div className="border-t border-white/5 p-3 space-y-3">
                {round.responses.map((response, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg bg-void-200/30 border border-white/5"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-200">
                          {response.role.replace("_", " ")}
                        </span>
                        <span className="text-xs text-slate-500">
                          {response.model.split("/").pop()}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-accent-primary">
                          {Math.round(response.confidence * 100)}%
                        </span>
                        {response.changed_from_previous && (
                          <Badge variant="warning" className="text-xs">
                            Changed
                          </Badge>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-slate-300 whitespace-pre-wrap">
                      {response.content}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// Metrics card
function MetricsCard({
  tokens,
  cost,
  duration,
  conferenceId,
}: {
  tokens: number;
  cost: number;
  duration: number;
  conferenceId: string;
}) {
  return (
    <Card variant="bordered" className="bg-void-200/20">
      <CardContent className="py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div>
              <p className="text-xs text-slate-500">Duration</p>
              <p className="text-sm font-mono text-slate-200">
                {formatDuration(duration)}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Tokens</p>
              <p className="text-sm font-mono text-slate-200">
                {formatTokens(tokens)}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Cost</p>
              <p className="text-sm font-mono text-slate-200">
                {formatCost(cost)}
              </p>
            </div>
          </div>

          <div className="text-right">
            <p className="text-xs text-slate-500">Conference ID</p>
            <p className="text-sm font-mono text-slate-400">{conferenceId}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

