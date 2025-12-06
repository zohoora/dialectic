"use client";

import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface RiskToleranceSliderProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}

const getLabel = (v: number) => {
  if (v < 0.3) return "Conservative";
  if (v < 0.7) return "Balanced";
  return "Exploratory";
};

const getDescription = (v: number) => {
  if (v < 0.3) return "Prioritize established guidelines. Speculator minimized.";
  if (v < 0.7) return "Full conference with balanced weighting between clinical evidence and exploratory ideas.";
  return "Weight novel approaches. Speculator emphasized.";
};

const getColor = (v: number) => {
  if (v < 0.3) return "bg-green-500";
  if (v < 0.7) return "bg-amber-500";
  return "bg-purple-500";
};

export function RiskToleranceSlider({ value, onChange, disabled }: RiskToleranceSliderProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs text-slate-400 uppercase tracking-wider">
          Risk Tolerance
        </label>
        <span className={cn(
          "text-xs font-medium px-2 py-0.5 rounded-full",
          value < 0.3 && "bg-green-500/20 text-green-400",
          value >= 0.3 && value < 0.7 && "bg-amber-500/20 text-amber-400",
          value >= 0.7 && "bg-purple-500/20 text-purple-400"
        )}>
          {getLabel(value)}
        </span>
      </div>
      
      <div className="space-y-2">
        <div className="flex items-center justify-between text-[10px] text-slate-500">
          <span>Conservative</span>
          <span>Exploratory</span>
        </div>
        
        <div className="relative">
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={value}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            disabled={disabled}
            className={cn(
              "w-full h-2 bg-slate-700 rounded-full appearance-none cursor-pointer",
              "[&::-webkit-slider-thumb]:appearance-none",
              "[&::-webkit-slider-thumb]:w-4",
              "[&::-webkit-slider-thumb]:h-4",
              "[&::-webkit-slider-thumb]:rounded-full",
              "[&::-webkit-slider-thumb]:bg-white",
              "[&::-webkit-slider-thumb]:shadow-lg",
              "[&::-webkit-slider-thumb]:cursor-pointer",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          />
          <div 
            className={cn("absolute top-0 left-0 h-2 rounded-full pointer-events-none", getColor(value))}
            style={{ width: `${value * 100}%` }}
          />
        </div>
        
        <div className="text-center">
          <span className="text-sm font-mono text-slate-300">{value.toFixed(1)}</span>
        </div>
      </div>
      
      <div className="rounded-md bg-slate-800/50 border border-slate-700/50 p-3">
        <div className="flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-slate-400">{getDescription(value)}</p>
        </div>
      </div>
    </div>
  );
}

