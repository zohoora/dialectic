"use client";

import { useState, ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface CollapsibleSectionProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  defaultOpen?: boolean;
  badge?: ReactNode;
  headerClassName?: string;
  contentClassName?: string;
  children: ReactNode;
}

export function CollapsibleSection({
  title,
  subtitle,
  icon,
  defaultOpen = false,
  badge,
  headerClassName,
  contentClassName,
  children,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="rounded-lg border border-slate-700/50 overflow-hidden">
      <button
        className={cn(
          "w-full flex items-center justify-between p-4 text-left",
          "hover:bg-white/[0.02] transition-colors",
          headerClassName
        )}
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-3">
          {icon && (
            <div className="p-2 rounded-lg bg-slate-800/50">
              {icon}
            </div>
          )}
          <div>
            <h3 className="font-medium text-slate-200">{title}</h3>
            {subtitle && (
              <p className="text-sm text-slate-400">{subtitle}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {badge}
          <ChevronDown 
            className={cn(
              "w-4 h-4 text-slate-400 transition-transform duration-200",
              isOpen && "rotate-180"
            )} 
          />
        </div>
      </button>
      
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className={cn("p-4 pt-0", contentClassName)}>
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

