"use client";

import { Brain, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";

interface LearningToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  disabled?: boolean;
}

export function LearningToggle({ enabled, onChange, disabled }: LearningToggleProps) {
  return (
    <Card className={cn(
      "border transition-colors",
      enabled 
        ? "bg-purple-900/20 border-purple-500/40" 
        : "bg-cyan-900/10 border-cyan-500/30"
    )}>
      <CardContent className="pt-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {enabled ? (
              <Brain className="w-5 h-5 text-purple-400" />
            ) : (
              <Cpu className="w-5 h-5 text-cyan-400" />
            )}
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-slate-200">
                  {enabled ? "Learning Mode (v3)" : "Fresh Analysis (v2.1)"}
                </span>
                <Badge className={cn(
                  "text-[10px]",
                  enabled 
                    ? "bg-purple-500/20 text-purple-300 border-purple-500/30"
                    : "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
                )}>
                  {enabled ? "v3" : "v2.1"}
                </Badge>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {enabled 
                  ? "Inject past heuristics • Extract new learnings • Build institutional memory"
                  : "No injected heuristics • Fresh perspective • No data stored"}
              </p>
            </div>
          </div>
          <Switch
            checked={enabled}
            onCheckedChange={onChange}
            disabled={disabled}
          />
        </div>
        
        {/* Feature comparison */}
        <div className={cn(
          "grid grid-cols-2 gap-2 text-[10px] pt-2 border-t",
          enabled ? "border-purple-500/20" : "border-cyan-500/20"
        )}>
          <div className={cn(
            "px-2 py-1.5 rounded",
            !enabled ? "bg-cyan-500/10 text-cyan-300" : "text-slate-500"
          )}>
            ✓ Two-lane deliberation
          </div>
          <div className={cn(
            "px-2 py-1.5 rounded",
            !enabled ? "bg-cyan-500/10 text-cyan-300" : "text-slate-500"
          )}>
            ✓ Scout literature
          </div>
          <div className={cn(
            "px-2 py-1.5 rounded",
            enabled ? "bg-purple-500/10 text-purple-300" : "text-slate-500"
          )}>
            {enabled ? "✓" : "○"} Heuristic injection
          </div>
          <div className={cn(
            "px-2 py-1.5 rounded",
            enabled ? "bg-purple-500/10 text-purple-300" : "text-slate-500"
          )}>
            {enabled ? "✓" : "○"} Learning extraction
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

