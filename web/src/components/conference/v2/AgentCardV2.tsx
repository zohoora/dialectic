"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, Check, X, Copy, CheckCheck } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Badge } from "@/components/ui/badge";
import { TypingIndicator } from "./TypingIndicator";
import { ConfidenceBadge } from "./ConfidenceMeter";
import { cn } from "@/lib/utils";

export type AgentRole = 
  | "empiricist"
  | "skeptic" 
  | "mechanist"
  | "speculator"
  | "pragmatist"
  | "patient_voice"
  | "arbitrator"
  | "advocate";

type AgentState = "waiting" | "streaming" | "complete" | "error";

interface Citation {
  text: string;
  verified: boolean | null; // null = pending verification
}

interface AgentCardV2Props {
  role: AgentRole;
  model?: string;
  content?: string;
  confidence?: number;
  citations?: Citation[];
  state?: AgentState;
  lane?: "A" | "B";
  positionChanged?: boolean;
  defaultExpanded?: boolean;
  maxCollapsedWords?: number;
  className?: string;
}

const AGENT_CONFIG: Record<AgentRole, {
  label: string;
  color: string;
  description: string;
}> = {
  empiricist: {
    label: "Empiricist",
    color: "var(--agent-empiricist)",
    description: "Evidence-based reasoning",
  },
  skeptic: {
    label: "Skeptic",
    color: "var(--agent-skeptic)",
    description: "Challenges assumptions",
  },
  mechanist: {
    label: "Mechanist",
    color: "var(--agent-mechanist)",
    description: "Pathophysiology focus",
  },
  speculator: {
    label: "Speculator",
    color: "var(--agent-speculator)",
    description: "Creative hypotheses",
  },
  pragmatist: {
    label: "Pragmatist",
    color: "var(--agent-pragmatist)",
    description: "Healthcare feasibility",
  },
  patient_voice: {
    label: "Patient Voice",
    color: "var(--agent-patient-voice)",
    description: "Patient perspective",
  },
  arbitrator: {
    label: "Arbitrator",
    color: "var(--agent-arbitrator)",
    description: "Synthesizes consensus",
  },
  advocate: {
    label: "Advocate",
    color: "var(--agent-advocate)",
    description: "Patient-centered outcomes",
  },
};

export function AgentCardV2({
  role,
  model,
  content = "",
  confidence = 50,
  citations = [],
  state = "waiting",
  lane,
  positionChanged = false,
  defaultExpanded = false,
  maxCollapsedWords = 150,
  className,
}: AgentCardV2Props) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);
  
  const config = AGENT_CONFIG[role] || AGENT_CONFIG.empiricist;
  
  // Truncate content for collapsed state
  const words = content.split(/\s+/);
  const isTruncated = words.length > maxCollapsedWords;
  const displayContent = isExpanded || !isTruncated
    ? content
    : words.slice(0, maxCollapsedWords).join(" ") + "...";

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Lane-specific border color
  const laneBorderClass = lane === "A" 
    ? "border-l-emerald-500" 
    : lane === "B" 
      ? "border-l-purple-500" 
      : "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-lg border transition-all duration-200",
        "bg-slate-800/30 border-slate-700/50",
        lane && `border-l-[3px] ${laneBorderClass}`,
        state === "streaming" && "streaming",
        `agent-glow-${role}`,
        className
      )}
      style={state === "streaming" ? {
        "--glow-color": config.color,
      } as React.CSSProperties : undefined}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 pb-2">
        <div className="flex items-center gap-3">
          {/* Agent Indicator */}
          <span 
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: config.color }}
          />
          
          {/* Agent Name */}
          <div>
            <span 
              className="font-semibold"
              style={{ color: config.color }}
            >
              {config.label}
            </span>
            {model && (
              <span className="text-xs text-slate-500 ml-2">
                ({model})
              </span>
            )}
          </div>
          
          {/* Position Changed Badge */}
          {positionChanged && (
            <Badge className="bg-amber-500/20 text-amber-300 text-xs">
              Position Changed
            </Badge>
          )}
        </div>
        
        {/* Confidence */}
        {state === "complete" && (
          <ConfidenceBadge percentage={confidence * 100} />
        )}
      </div>
      
      {/* Content */}
      <div className="px-4 pb-4">
        {state === "waiting" && (
          <div className="py-4">
            <div className="h-4 bg-slate-700/50 rounded animate-pulse w-3/4 mb-2" />
            <div className="h-4 bg-slate-700/50 rounded animate-pulse w-1/2" />
          </div>
        )}
        
        {state === "streaming" && (
          <div className="space-y-3">
            {content ? (
              <div className="prose prose-sm prose-invert max-w-none">
                <ReactMarkdown>{content}</ReactMarkdown>
              </div>
            ) : null}
            <TypingIndicator agentColor={config.color} />
          </div>
        )}
        
        {state === "complete" && (
          <div className="space-y-3">
            {/* Main Content */}
            <div className="prose prose-sm prose-invert max-w-none">
              <ReactMarkdown>{displayContent}</ReactMarkdown>
            </div>
            
            {/* Citations with Verification */}
            {citations.length > 0 && (
              <div className="pt-2 border-t border-slate-700/50">
                <p className="text-xs text-slate-500 mb-2">Citations:</p>
                <div className="space-y-1">
                  {citations.map((citation, idx) => (
                    <div 
                      key={idx}
                      className="flex items-start gap-2 text-sm"
                    >
                      {citation.verified === true && (
                        <Check className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                      )}
                      {citation.verified === false && (
                        <X className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                      )}
                      {citation.verified === null && (
                        <span className="w-4 h-4 rounded-full bg-slate-600 animate-pulse flex-shrink-0 mt-0.5" />
                      )}
                      <span className="text-slate-300">{citation.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Expand/Copy Controls */}
            <div className="flex items-center justify-between pt-2">
              {isTruncated && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-300"
                >
                  <ChevronDown className={cn(
                    "w-4 h-4 transition-transform",
                    isExpanded && "rotate-180"
                  )} />
                  {isExpanded ? "Show less" : "Expand full"}
                </button>
              )}
              
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-300 ml-auto"
              >
                {copied ? (
                  <>
                    <CheckCheck className="w-3.5 h-3.5" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    Copy
                  </>
                )}
              </button>
            </div>
          </div>
        )}
        
        {state === "error" && (
          <div className="py-4 text-red-400 text-sm">
            An error occurred while generating this response.
          </div>
        )}
      </div>
    </motion.div>
  );
}

