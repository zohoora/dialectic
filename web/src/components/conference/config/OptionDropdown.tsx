"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface DropdownOption<T extends string> {
  value: T;
  label: string;
  description: string;
  icon: React.ElementType;
  color: string;
}

interface OptionDropdownProps<T extends string> {
  label: string;
  value: T;
  options: DropdownOption<T>[];
  onChange: (value: T) => void;
  disabled?: boolean;
}

export function OptionDropdown<T extends string>({ 
  label, 
  value, 
  options, 
  onChange, 
  disabled 
}: OptionDropdownProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const selectedOption = options.find(opt => opt.value === value) || options[0];
  const Icon = selectedOption.icon;
  
  return (
    <div className="space-y-2">
      <label className="text-xs text-slate-400 uppercase tracking-wider">
        {label}
      </label>
      
      <div className="relative">
        <button
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={cn(
            "w-full flex items-center justify-between px-3 py-2.5 rounded-lg",
            "bg-slate-800 border border-slate-700 text-left",
            "hover:border-slate-600 transition-colors",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        >
          <div className="flex items-center gap-2">
            <Icon className={cn("w-4 h-4", selectedOption.color)} />
            <span className="text-sm text-slate-200">{selectedOption.label}</span>
          </div>
          <ChevronDown className={cn(
            "w-4 h-4 text-slate-400 transition-transform",
            isOpen && "rotate-180"
          )} />
        </button>
        
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-full left-0 right-0 mt-1 z-50 rounded-lg bg-slate-800 border border-slate-700 shadow-xl overflow-hidden max-h-60 overflow-y-auto"
            >
              {options.map((option) => {
                const OptionIcon = option.icon;
                return (
                  <button
                    key={option.value}
                    onClick={() => {
                      onChange(option.value);
                      setIsOpen(false);
                    }}
                    className={cn(
                      "w-full flex items-start gap-3 px-3 py-3 text-left",
                      "hover:bg-slate-700/50 transition-colors",
                      option.value === value && "bg-slate-700/30"
                    )}
                  >
                    <OptionIcon className={cn("w-4 h-4 mt-0.5", option.color)} />
                    <div>
                      <div className="text-sm text-slate-200">{option.label}</div>
                      <div className="text-xs text-slate-500">{option.description}</div>
                    </div>
                    {option.value === value && (
                      <span className="ml-auto text-cyan-400">✓</span>
                    )}
                  </button>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

