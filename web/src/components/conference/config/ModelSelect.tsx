"use client";

import { cn } from "@/lib/utils";
import { MODEL_OPTIONS, MODEL_COMPONENT_INFO } from "./constants";
import type { V3ModelConfig } from "./types";

interface ModelSelectProps {
  componentKey: keyof V3ModelConfig;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function ModelSelect({ componentKey, value, onChange, disabled }: ModelSelectProps) {
  const info = MODEL_COMPONENT_INFO[componentKey];
  
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-xs text-slate-400">{info.label}</label>
        <span className="text-[10px] text-slate-500">{info.recommendation}</span>
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={cn(
          "w-full h-8 px-2 rounded-md border bg-slate-900 text-slate-200 text-xs",
          "border-slate-700 focus:border-purple-500/50 focus:outline-none",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <optgroup label="⚡ Fast (Low Cost)">
          {MODEL_OPTIONS.filter(m => m.category === "fast").map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </optgroup>
        <optgroup label="⚖️ Balanced">
          {MODEL_OPTIONS.filter(m => m.category === "balanced").map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </optgroup>
        <optgroup label="🚀 Powerful">
          {MODEL_OPTIONS.filter(m => m.category === "powerful").map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </optgroup>
        <optgroup label="🧠 Deep Reasoning">
          {MODEL_OPTIONS.filter(m => m.category === "reasoning").map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </optgroup>
      </select>
      <p className="text-[10px] text-slate-500">{info.description}</p>
    </div>
  );
}

