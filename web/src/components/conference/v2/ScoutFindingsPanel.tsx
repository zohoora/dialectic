"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Search, 
  ChevronDown, 
  ChevronUp,
  BookOpen,
  AlertCircle
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PaperCard } from "./PaperCard";
import { EvidenceGradeBadge, EvidenceGrade } from "./EvidenceGradeBadge";
import { cn } from "@/lib/utils";

interface ScoutCitation {
  title: string;
  authors: string[];
  journal: string;
  year: number;
  pmid?: string;
  doi?: string;
  evidence_grade: EvidenceGrade;
  key_finding: string;
  sample_size?: number;
}

interface ScoutReport {
  is_empty: boolean;
  query_keywords: string[];
  total_results_found: number;
  meta_analyses: ScoutCitation[];
  high_quality_rcts: ScoutCitation[];
  preliminary_evidence: ScoutCitation[];
  conflicting_evidence: ScoutCitation[];
}

interface ScoutFindingsPanelProps {
  report: ScoutReport;
  isLoading?: boolean;
  className?: string;
}

function CitationCategory({
  title,
  icon,
  color,
  citations,
  defaultShowCount = 2,
}: {
  title: string;
  icon: string;
  color: string;
  citations: ScoutCitation[];
  defaultShowCount?: number;
}) {
  const [showAll, setShowAll] = useState(false);
  
  if (citations.length === 0) return null;
  
  const displayedCitations = showAll 
    ? citations 
    : citations.slice(0, defaultShowCount);
  const hiddenCount = citations.length - defaultShowCount;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium flex items-center gap-2" style={{ color }}>
          <span>{icon}</span>
          <span>{title} ({citations.length})</span>
        </h4>
        {hiddenCount > 0 && !showAll && (
          <button
            onClick={() => setShowAll(true)}
            className="text-xs text-slate-400 hover:text-slate-300"
          >
            +{hiddenCount} more
          </button>
        )}
      </div>
      
      <div className="space-y-2">
        {displayedCitations.map((citation, idx) => (
          <PaperCard
            key={`${citation.pmid || idx}`}
            title={citation.title}
            journal={citation.journal}
            year={citation.year}
            pmid={citation.pmid}
            sampleSize={citation.sample_size}
            keyFinding={citation.key_finding}
            evidenceGrade={citation.evidence_grade}
            isPreprint={citation.evidence_grade === "preprint"}
          />
        ))}
      </div>
      
      {showAll && hiddenCount > 0 && (
        <button
          onClick={() => setShowAll(false)}
          className="text-xs text-slate-400 hover:text-slate-300"
        >
          Show less
        </button>
      )}
    </div>
  );
}

export function ScoutFindingsPanel({
  report,
  isLoading = false,
  className,
}: ScoutFindingsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const totalCitations = 
    report.meta_analyses.length +
    report.high_quality_rcts.length +
    report.preliminary_evidence.length +
    report.conflicting_evidence.length;

  // Auto-expand if few results
  const shouldDefaultExpand = totalCitations > 0 && totalCitations <= 5;
  const actualExpanded = isExpanded || shouldDefaultExpand;

  // Empty state
  if (report.is_empty && !isLoading) {
    return (
      <div className={cn(
        "rounded-lg border border-slate-700/50 bg-slate-800/30 p-4",
        className
      )}>
        <div className="flex items-center gap-3 text-slate-400">
          <BookOpen className="w-5 h-5" />
          <div>
            <p className="text-sm">No recent publications found</p>
            <p className="text-xs text-slate-500">
              Keywords searched: {report.query_keywords.join(", ")}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className={cn(
        "rounded-lg border border-lime-500/30 bg-lime-900/10 p-4",
        "animate-pulse",
        className
      )}>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-lime-500/20">
            <Search className="w-4 h-4 text-lime-400 animate-pulse" />
          </div>
          <div>
            <p className="text-sm text-lime-300">Searching recent literature...</p>
            <p className="text-xs text-slate-400">
              Keywords: {report.query_keywords.join(", ")}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      "rounded-lg border border-lime-500/30 bg-lime-900/10 overflow-hidden",
      className
    )}>
      {/* Header */}
      <button
        className="w-full flex items-center justify-between p-4 hover:bg-lime-900/20 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-lime-500/20">
            <Search className="w-4 h-4 text-lime-400" />
          </div>
          <div className="text-left">
            <h3 className="font-medium text-lime-300">Scout Literature Search</h3>
            <p className="text-xs text-slate-400">
              {totalCitations} papers • Keywords: {report.query_keywords.slice(0, 3).join(", ")}
              {report.query_keywords.length > 3 && "..."}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Quick stats badges */}
          {report.meta_analyses.length > 0 && (
            <Badge className="bg-purple-500/20 text-purple-300 text-xs">
              {report.meta_analyses.length} Meta
            </Badge>
          )}
          {report.high_quality_rcts.length > 0 && (
            <Badge className="bg-green-500/20 text-green-300 text-xs">
              {report.high_quality_rcts.length} RCT
            </Badge>
          )}
          {report.conflicting_evidence.length > 0 && (
            <Badge className="bg-red-500/20 text-red-300 text-xs">
              {report.conflicting_evidence.length} Conflict
            </Badge>
          )}
          
          {actualExpanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      <AnimatePresence initial={false}>
        {actualExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-4 pb-4 space-y-6">
              {/* Meta-Analyses */}
              <CitationCategory
                title="META-ANALYSES & SYSTEMATIC REVIEWS"
                icon="🟣"
                color="var(--evidence-meta)"
                citations={report.meta_analyses}
              />
              
              {/* RCTs */}
              <CitationCategory
                title="RANDOMIZED CONTROLLED TRIALS"
                icon="🟢"
                color="var(--evidence-rct)"
                citations={report.high_quality_rcts}
              />
              
              {/* Preliminary */}
              <CitationCategory
                title="PRELIMINARY EVIDENCE"
                icon="🟡"
                color="var(--evidence-observational)"
                citations={report.preliminary_evidence}
              />
              
              {/* Conflicting */}
              {report.conflicting_evidence.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-red-400">
                    <AlertCircle className="w-4 h-4" />
                    <h4 className="text-sm font-medium">
                      CONFLICTING EVIDENCE ({report.conflicting_evidence.length})
                    </h4>
                  </div>
                  <p className="text-xs text-slate-400">
                    ⚠️ These findings conflict with other evidence — acknowledge but do not auto-resolve
                  </p>
                  <div className="space-y-2">
                    {report.conflicting_evidence.map((citation, idx) => (
                      <PaperCard
                        key={`${citation.pmid || idx}`}
                        title={citation.title}
                        journal={citation.journal}
                        year={citation.year}
                        pmid={citation.pmid}
                        sampleSize={citation.sample_size}
                        keyFinding={citation.key_finding}
                        evidenceGrade="conflicting"
                      />
                    ))}
                  </div>
                </div>
              )}
              
              {/* Interpretation Guide */}
              <div className="pt-4 border-t border-slate-700/50">
                <p className="text-xs text-slate-500">
                  <strong>Scout Interpretation:</strong>{" "}
                  🟣 High weight — may update guidelines •{" "}
                  🟢 High weight — strong if methodology sound •{" "}
                  🟡 Signal only — do not present as established fact •{" "}
                  🔴 Conflicting — acknowledge, don&apos;t resolve
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

