"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, FileText, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LIBRARIAN_MODEL_OPTIONS } from "./constants";
import type { LibrarianConfig } from "./types";

interface LibrarianConfigSectionProps {
  config: LibrarianConfig;
  onChange: (config: LibrarianConfig) => void;
  disabled?: boolean;
  hasFiles?: boolean;
}

export function LibrarianConfigSection({ config, onChange, disabled, hasFiles }: LibrarianConfigSectionProps) {
  const [expanded, setExpanded] = useState(false);
  
  return (
    <Card className={cn(
      "border transition-colors",
      hasFiles 
        ? "bg-indigo-900/20 border-indigo-500/40" 
        : "bg-slate-800/30 border-slate-700/50"
    )}>
      <CardHeader
        className="py-3 px-4 cursor-pointer hover:bg-slate-800/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-indigo-400" />
            <span className="text-sm font-medium text-slate-200">Librarian (Document Analysis)</span>
            {hasFiles && (
              <Badge className="text-[10px] bg-indigo-500/20 text-indigo-300 border-indigo-500/30">
                Active
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!hasFiles && (
              <span className="text-xs text-slate-500">Upload files to enable</span>
            )}
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </div>
      </CardHeader>
      
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ opacity: 0, height: 0 }}
          >
            <CardContent className="pt-0 space-y-4">
              {/* Model Selection */}
              <div className="space-y-2">
                <label className="text-xs text-slate-400 uppercase tracking-wider">
                  Analysis Model
                </label>
                <select
                  value={config.model}
                  onChange={(e) => onChange({ ...config, model: e.target.value })}
                  disabled={disabled}
                  className={cn(
                    "w-full h-9 px-3 rounded-md border bg-slate-900 text-slate-200 text-sm",
                    "border-slate-700 focus:border-indigo-500/50 focus:outline-none",
                    disabled && "opacity-50 cursor-not-allowed"
                  )}
                >
                  <optgroup label="⭐ Recommended (Large Context)">
                    {LIBRARIAN_MODEL_OPTIONS.filter(m => m.recommended).map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </optgroup>
                  <optgroup label="Other Options">
                    {LIBRARIAN_MODEL_OPTIONS.filter(m => !m.recommended).map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </optgroup>
                </select>
                <p className="text-xs text-slate-500">
                  Models with larger context windows can handle more documents
                </p>
              </div>
              
              {/* Max Queries Per Turn */}
              <div className="space-y-2">
                <label className="text-xs text-slate-400 uppercase tracking-wider">
                  Max Queries Per Turn
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={config.maxQueriesPerTurn}
                    onChange={(e) => onChange({ ...config, maxQueriesPerTurn: parseInt(e.target.value) })}
                    disabled={disabled}
                    className={cn(
                      "flex-1 h-2 bg-slate-700 rounded-full appearance-none cursor-pointer",
                      disabled && "opacity-50 cursor-not-allowed"
                    )}
                  />
                  <span className="text-sm font-mono text-slate-300 w-6 text-center">
                    {config.maxQueriesPerTurn}
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  How many document lookups each agent can request per turn
                </p>
              </div>
              
              {/* Info note */}
              <div className="rounded-md bg-indigo-500/10 border border-indigo-500/30 p-3">
                <div className="flex items-start gap-2">
                  <Info className="w-3.5 h-3.5 text-indigo-400 mt-0.5 flex-shrink-0" />
                  <div className="text-xs text-slate-400">
                    <p>The Librarian analyzes uploaded documents and makes relevant information available to agents during deliberation.</p>
                    {!hasFiles && (
                      <p className="mt-1 text-indigo-300">Upload documents above to activate the Librarian.</p>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

