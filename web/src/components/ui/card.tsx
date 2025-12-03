"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "glass" | "bordered";
  glow?: "cyan" | "purple" | "green" | "red" | "yellow" | "none";
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = "default", glow = "none", ...props }, ref) => {
    const variants = {
      default: "bg-void-200/50 border-white/5",
      glass: "glass",
      bordered: "bg-transparent border-white/10",
    };

    const glows = {
      none: "",
      cyan: "shadow-[0_0_30px_rgba(34,211,238,0.1)] border-cyan-500/20",
      purple: "shadow-[0_0_30px_rgba(168,85,247,0.1)] border-purple-500/20",
      green: "shadow-[0_0_30px_rgba(34,197,94,0.1)] border-green-500/20",
      red: "shadow-[0_0_30px_rgba(239,68,68,0.1)] border-red-500/20",
      yellow: "shadow-[0_0_30px_rgba(245,158,11,0.1)] border-yellow-500/20",
    };

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-xl border p-4 transition-all duration-300",
          variants[variant],
          glows[glow],
          className
        )}
        {...props}
      />
    );
  }
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 pb-4", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-lg font-semibold leading-none tracking-tight text-slate-100",
      className
    )}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-slate-400", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("", className)} {...props} />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center pt-4 border-t border-white/5", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter };

