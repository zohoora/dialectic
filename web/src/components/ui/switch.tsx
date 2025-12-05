"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> {
  label?: string;
  onCheckedChange?: (checked: boolean) => void;
  onChange?: React.ChangeEventHandler<HTMLInputElement>;
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, label, checked, onChange, onCheckedChange, ...props }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange?.(e);
      onCheckedChange?.(e.target.checked);
    };
    return (
      <label className="inline-flex items-center gap-3 cursor-pointer">
        <div className="relative">
          <input
            type="checkbox"
            ref={ref}
            checked={checked}
            onChange={handleChange}
            className="sr-only peer"
            {...props}
          />
          <div
            className={cn(
              "w-11 h-6 rounded-full transition-all duration-200",
              "bg-void-300 peer-checked:bg-accent-primary/30",
              "border border-white/10 peer-checked:border-accent-primary/50",
              className
            )}
          />
          <div
            className={cn(
              "absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-all duration-200",
              "bg-slate-400 peer-checked:bg-accent-primary",
              "peer-checked:translate-x-5",
              "shadow-sm peer-checked:shadow-glow-sm"
            )}
          />
        </div>
        {label && <span className="text-sm text-slate-300">{label}</span>}
      </label>
    );
  }
);
Switch.displayName = "Switch";

export { Switch };

