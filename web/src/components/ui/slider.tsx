"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SliderProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
  showValue?: boolean;
}

const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
  ({ className, label, showValue = true, value, min = 0, max = 100, ...props }, ref) => {
    return (
      <div className="space-y-3">
        {(label || showValue) && (
          <div className="flex items-center justify-between">
            {label && <span className="text-sm text-slate-400">{label}</span>}
            {showValue && (
              <span className="text-sm font-mono font-semibold text-slate-200 bg-void-300 px-2.5 py-1 rounded-md border border-white/10">
                {value}
              </span>
            )}
          </div>
        )}
        <div className="relative py-1">
          <input
            type="range"
            ref={ref}
            value={value}
            min={min}
            max={max}
            className={cn(
              "w-full h-1.5 rounded-full appearance-none cursor-pointer",
              "bg-slate-700/50",
              // Webkit (Chrome, Safari) thumb styling
              "[&::-webkit-slider-thumb]:appearance-none",
              "[&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5",
              "[&::-webkit-slider-thumb]:rounded-full",
              "[&::-webkit-slider-thumb]:bg-white",
              "[&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-accent-primary",
              "[&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:shadow-accent-primary/30",
              "[&::-webkit-slider-thumb]:cursor-pointer",
              "[&::-webkit-slider-thumb]:transition-all [&::-webkit-slider-thumb]:duration-150",
              "[&::-webkit-slider-thumb]:hover:scale-110 [&::-webkit-slider-thumb]:hover:shadow-xl",
              "[&::-webkit-slider-thumb]:active:scale-95",
              // Firefox thumb styling
              "[&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:h-5",
              "[&::-moz-range-thumb]:rounded-full",
              "[&::-moz-range-thumb]:bg-white",
              "[&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-accent-primary",
              "[&::-moz-range-thumb]:cursor-pointer",
              "[&::-moz-range-thumb]:transition-all",
              // Track styling
              "[&::-webkit-slider-runnable-track]:rounded-full",
              "[&::-moz-range-track]:rounded-full",
              className
            )}
            {...props}
          />
        </div>
      </div>
    );
  }
);
Slider.displayName = "Slider";

export { Slider };

