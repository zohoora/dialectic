"use client";

import { motion } from "framer-motion";
import { 
  CheckCircle, 
  Lightbulb, 
  Shield, 
  AlertTriangle,
  RefreshCw,
  Copy,
  CheckCheck,
  FileText
} from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { ConfidenceMeter, ConfidenceBadge } from "./ConfidenceMeter";
import { cn } from "@/lib/utils";

// Types
interface ClinicalConsensus {
  recommendation: string;
  evidence_basis: string[];
  confidence: number;
  safety_profile: string;
  contraindications: string[];
  monitoring_required?: string[];
}

interface ExploratoryConsideration {
  hypothesis: string;
  mechanism: string;
  evidence_level: "theoretical" | "preclinical" | "early_clinical" | "off_label";
  potential_benefit: string;
  risks: string[];
  what_would_validate: string;
}

interface Tension {
  description: string;
  lane_a_position: string;
  lane_b_position: string;
  resolution: string;
  what_would_resolve?: string;
}

interface ArbitratorSynthesis {
  clinical_consensus: ClinicalConsensus;
  exploratory_considerations: ExploratoryConsideration[];
  tensions: Tension[];
  safety_concerns_raised: string[];
  stagnation_concerns_raised: string[];
  what_would_change_mind: string;
  preserved_dissent: string[];
  overall_confidence: number;
}

interface SynthesisViewProps {
  synthesis: ArbitratorSynthesis;
  className?: string;
}

const EVIDENCE_LEVEL_CONFIG = {
  theoretical: { label: "Theoretical", color: "#a855f7", icon: "🔮" },
  preclinical: { label: "Preclinical", color: "#fb923c", icon: "🧪" },
  early_clinical: { label: "Early Clinical", color: "#facc15", icon: "📊" },
  off_label: { label: "Off-Label", color: "#22c55e", icon: "💊" },
};

function ClinicalConsensusCard({ consensus }: { consensus: ClinicalConsensus }) {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(consensus.recommendation);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card className="bg-emerald-900/10 border-emerald-500/30">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🟢</span>
            <div>
              <h3 className="font-semibold text-emerald-300">Clinical Consensus</h3>
              <p className="text-xs text-slate-400">Evidence-based recommendation</p>
            </div>
          </div>
          <ConfidenceBadge percentage={consensus.confidence * 100} />
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Main Recommendation */}
        <div>
          <h4 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Recommendation</h4>
          <div className="prose prose-sm prose-invert max-w-none">
            <ReactMarkdown>{consensus.recommendation}</ReactMarkdown>
          </div>
          <button
            onClick={handleCopy}
            className="mt-2 flex items-center gap-1 text-xs text-slate-400 hover:text-slate-300"
          >
            {copied ? <CheckCheck className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? "Copied!" : "Copy recommendation"}
          </button>
        </div>
        
        {/* Evidence Basis */}
        {consensus.evidence_basis.length > 0 && (
          <div>
            <h4 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Evidence Basis</h4>
            <ul className="space-y-1">
              {consensus.evidence_basis.map((evidence, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-slate-300">
                  <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  {evidence}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Confidence Meter */}
        <div>
          <h4 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Confidence</h4>
          <ConfidenceMeter percentage={consensus.confidence * 100} />
        </div>
        
        {/* Safety Profile */}
        {consensus.safety_profile && (
          <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-4 h-4 text-cyan-400" />
              <h4 className="text-xs text-cyan-400 font-medium">Safety Considerations</h4>
            </div>
            <div className="prose prose-sm prose-invert max-w-none text-slate-300">
              <ReactMarkdown>{consensus.safety_profile}</ReactMarkdown>
            </div>
          </div>
        )}
        
        {/* Contraindications */}
        {consensus.contraindications.length > 0 && (
          <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/20">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <h4 className="text-xs text-red-400 font-medium">Contraindications</h4>
            </div>
            <ul className="space-y-1">
              {consensus.contraindications.map((item, idx) => (
                <li key={idx} className="text-sm text-slate-300">• {item}</li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Monitoring */}
        {consensus.monitoring_required && consensus.monitoring_required.length > 0 && (
          <div>
            <h4 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Monitoring Plan</h4>
            <ul className="space-y-1">
              {consensus.monitoring_required.map((item, idx) => (
                <li key={idx} className="text-sm text-slate-300">• {item}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ExploratoryConsiderationsCard({ 
  considerations 
}: { 
  considerations: ExploratoryConsideration[] 
}) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  
  if (considerations.length === 0) {
    return null;
  }

  return (
    <Card className="bg-purple-900/10 border-purple-500/30">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🟣</span>
          <div>
            <h3 className="font-semibold text-purple-300">Exploratory Considerations</h3>
            <p className="text-xs text-slate-400">Theoretical approaches requiring validation</p>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 p-2 rounded bg-amber-500/10 border border-amber-500/20">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <span className="text-xs text-amber-300">
            These are theoretical approaches — do not present as established fact
          </span>
        </div>
        
        {considerations.map((consideration, idx) => {
          const levelConfig = EVIDENCE_LEVEL_CONFIG[consideration.evidence_level];
          const isExpanded = expandedIdx === idx;
          
          return (
            <div
              key={idx}
              className={cn(
                "rounded-lg border border-purple-500/20 bg-slate-800/30",
                "transition-all duration-200",
                isExpanded && "border-purple-500/40"
              )}
            >
              <button
                className="w-full p-4 text-left"
                onClick={() => setExpandedIdx(isExpanded ? null : idx)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge 
                        className="text-xs"
                        style={{ 
                          backgroundColor: `${levelConfig.color}20`,
                          color: levelConfig.color,
                        }}
                      >
                        {levelConfig.icon} {levelConfig.label}
                      </Badge>
                    </div>
                    <h4 className="font-medium text-slate-200">{consideration.hypothesis}</h4>
                  </div>
                  <Lightbulb className={cn(
                    "w-5 h-5 text-purple-400 transition-transform",
                    isExpanded && "rotate-12"
                  )} />
                </div>
              </button>
              
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  className="px-4 pb-4 space-y-3"
                >
                  {/* Mechanism */}
                  {consideration.mechanism && (
                    <div>
                      <h5 className="text-xs text-slate-500 mb-1">Mechanism</h5>
                      <div className="prose prose-sm prose-invert max-w-none text-slate-300">
                        <ReactMarkdown>{consideration.mechanism}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                  
                  {/* Potential Benefit */}
                  {consideration.potential_benefit && (
                    <div>
                      <h5 className="text-xs text-slate-500 mb-1">Potential Benefit</h5>
                      <div className="prose prose-sm prose-invert max-w-none text-slate-300">
                        <ReactMarkdown>{consideration.potential_benefit}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                  
                  {/* Risks */}
                  {consideration.risks.length > 0 && (
                    <div>
                      <h5 className="text-xs text-slate-500 mb-1">Risks</h5>
                      <div className="prose prose-sm prose-invert max-w-none text-slate-300 space-y-1">
                        {consideration.risks.map((risk, ridx) => (
                          <div key={ridx}>
                            <ReactMarkdown>{`• ${risk}`}</ReactMarkdown>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* What Would Validate */}
                  {consideration.what_would_validate && (
                    <div className="p-3 rounded-lg bg-cyan-500/5 border border-cyan-500/20">
                      <h5 className="text-xs text-cyan-400 font-medium mb-1">What Would Validate</h5>
                      <div className="prose prose-sm prose-invert max-w-none text-slate-300">
                        <ReactMarkdown>{consideration.what_would_validate}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

export function SynthesisView({ synthesis, className }: SynthesisViewProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("space-y-6", className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-500/20">
            <FileText className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Arbitrator Synthesis</h2>
            <p className="text-sm text-slate-400">
              Overall Confidence: {Math.round(synthesis.overall_confidence * 100)}%
            </p>
          </div>
        </div>
        <ConfidenceBadge percentage={synthesis.overall_confidence * 100} />
      </div>
      
      {/* Two-Lane Results */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ClinicalConsensusCard consensus={synthesis.clinical_consensus} />
        <ExploratoryConsiderationsCard considerations={synthesis.exploratory_considerations} />
      </div>
      
      {/* Tensions */}
      {synthesis.tensions.length > 0 && (
        <Card className="bg-amber-900/10 border-amber-500/30">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <span className="text-xl">⚡</span>
              <h3 className="font-semibold text-amber-300">Tensions</h3>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {synthesis.tensions.map((tension, idx) => (
              <div key={idx} className="p-4 rounded-lg bg-slate-800/30 border border-slate-700/50">
                <div className="prose prose-sm prose-invert max-w-none text-slate-300 mb-3">
                  <ReactMarkdown>{tension.description}</ReactMarkdown>
                </div>
                {tension.what_would_resolve && (
                  <div className="p-2 rounded bg-cyan-500/10 border border-cyan-500/20">
                    <span className="text-xs text-cyan-400 font-medium">What Would Resolve: </span>
                    <span className="text-xs text-slate-300">{tension.what_would_resolve}</span>
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
      
      {/* What Would Change This */}
      {synthesis.what_would_change_mind && (
        <Card className="bg-slate-800/30 border-slate-700/50">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-cyan-400" />
              <h3 className="font-medium text-slate-300">What Would Change This Recommendation</h3>
            </div>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm prose-invert max-w-none text-slate-400">
              <ReactMarkdown>{synthesis.what_would_change_mind}</ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Preserved Dissent */}
      {synthesis.preserved_dissent.length > 0 && (
        <Card className="bg-slate-800/30 border-slate-700/50">
          <CardHeader className="pb-2">
            <h3 className="font-medium text-slate-300">Preserved Dissent</h3>
          </CardHeader>
          <CardContent className="space-y-3">
            {synthesis.preserved_dissent.map((dissent, idx) => (
              <div key={idx} className="prose prose-sm prose-invert max-w-none text-slate-400 pl-4 border-l-2 border-slate-600">
                <ReactMarkdown>{dissent}</ReactMarkdown>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}

