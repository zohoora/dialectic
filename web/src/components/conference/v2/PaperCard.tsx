"use client";

import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { EvidenceGradeBadge, EvidenceGrade } from "./EvidenceGradeBadge";
import { cn } from "@/lib/utils";

interface PaperCardProps {
  title: string;
  journal: string;
  year: number;
  pmid?: string;
  doi?: string;
  sampleSize?: number;
  keyFinding: string;
  evidenceGrade: EvidenceGrade;
  isPreprint?: boolean;
  className?: string;
}

export function PaperCard({
  title,
  journal,
  year,
  pmid,
  doi,
  sampleSize,
  keyFinding,
  evidenceGrade,
  isPreprint = false,
  className,
}: PaperCardProps) {
  const pubmedUrl = pmid ? `https://pubmed.ncbi.nlm.nih.gov/${pmid}` : undefined;
  const doiUrl = doi ? `https://doi.org/${doi}` : undefined;
  const linkUrl = pubmedUrl || doiUrl;

  return (
    <div 
      className={cn(
        "p-4 rounded-lg border transition-all duration-200",
        "bg-slate-800/30 border-slate-700/50",
        "hover:bg-slate-800/50 hover:border-slate-600/50",
        isPreprint && "border-dashed",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <EvidenceGradeBadge grade={evidenceGrade} size="sm" />
          {isPreprint && (
            <Badge className="bg-orange-500/20 text-orange-300 text-xs">
              PREPRINT
            </Badge>
          )}
        </div>
        {linkUrl && (
          <a
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 hover:text-cyan-400 transition-colors"
            title="View publication"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>
      
      {/* Title */}
      <h4 className="font-medium text-slate-200 mb-2 leading-snug">
        {title}
      </h4>
      
      {/* Meta */}
      <div className="flex items-center gap-2 text-xs text-slate-400 mb-3 flex-wrap">
        <span>{journal}</span>
        <span>•</span>
        <span>{year}</span>
        {sampleSize && (
          <>
            <span>•</span>
            <span className="text-emerald-400">n={sampleSize.toLocaleString()}</span>
          </>
        )}
        {pmid && (
          <>
            <span>•</span>
            <a 
              href={pubmedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:underline"
            >
              PMID: {pmid}
            </a>
          </>
        )}
      </div>
      
      {/* Key Finding */}
      <div className="text-sm">
        <span className="text-slate-500 font-medium">Finding: </span>
        <span className="text-slate-300">{keyFinding}</span>
      </div>
    </div>
  );
}

