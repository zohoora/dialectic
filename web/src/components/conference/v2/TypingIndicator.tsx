"use client";

import { cn } from "@/lib/utils";

interface TypingIndicatorProps {
  agentColor?: string;
  className?: string;
}

export function TypingIndicator({ 
  agentColor = "var(--status-active)", 
  className 
}: TypingIndicatorProps) {
  return (
    <div className={cn("flex items-center gap-1 p-2", className)}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="typing-dot"
          style={{ backgroundColor: agentColor }}
        />
      ))}
    </div>
  );
}

// Text-based fallback for reduced motion
export function TypingIndicatorStatic({ className }: { className?: string }) {
  return (
    <span className={cn("text-sm text-slate-400 italic", className)}>
      Thinking...
    </span>
  );
}

