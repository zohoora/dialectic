"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SliderProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
  showValue?: boolean;
}

const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
  ({ className, label, showValue = true, value, min = 0, max = 100, ...props }, ref) => {
    const percentage = ((Number(value) - Number(min)) / (Number(max) - Number(min))) * 100;

    return (
      <div className="space-y-2">
        {(label || showValue) && (
          <div className="flex items-center justify-between">
            {label && <span className="text-sm text-slate-400">{label}</span>}
            {showValue && (
              <span className="text-sm font-mono text-accent-primary">{value}</span>
            )}
          </div>
        )}
        <div className="relative">
          <input
            type="range"
            ref={ref}
            value={value}
            min={min}
            max={max}
            className={cn(
              "w-full h-2 rounded-full appearance-none cursor-pointer bg-void-300",
              "[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent-primary [&::-webkit-slider-thumb]:shadow-glow-sm [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:transition-all [&::-webkit-slider-thumb]:hover:scale-110",
              "[&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-accent-primary [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:cursor-pointer",
              className
            )}
            style={{
              background: `linear-gradient(to right, rgb(34 211 238 / 0.5) 0%, rgb(34 211 238 / 0.5) ${percentage}%, rgb(26 35 46) ${percentage}%, rgb(26 35 46) 100%)`,
            }}
            {...props}
          />
        </div>
      </div>
    );
  }
);
Slider.displayName = "Slider";

export { Slider };

