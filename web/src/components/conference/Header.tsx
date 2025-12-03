"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Activity, Settings, Key, Check, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface HeaderProps {
  apiKey: string;
  onApiKeyChange: (key: string) => void;
  isConnected: boolean;
  conferenceStatus: "idle" | "running" | "complete" | "error";
}

export function Header({
  apiKey,
  onApiKeyChange,
  isConnected,
  conferenceStatus,
}: HeaderProps) {
  const [showApiKeyInput, setShowApiKeyInput] = useState(!apiKey);
  const [tempApiKey, setTempApiKey] = useState(apiKey);

  const handleSaveApiKey = () => {
    onApiKeyChange(tempApiKey);
    setShowApiKeyInput(false);
  };

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-void/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo / Title */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-primary to-accent-secondary flex items-center justify-center">
              <Activity className="w-5 h-5 text-void" />
            </div>
            {/* Status indicator */}
            <div
              className={cn(
                "absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-void",
                isConnected ? "bg-green-500" : "bg-red-500"
              )}
            />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-slate-100 tracking-tight">
              Case Conference
            </h1>
            <p className="text-xs text-slate-500">
              Multi-agent clinical deliberation
            </p>
          </div>
        </div>

        {/* Status / Controls */}
        <div className="flex items-center gap-4">
          {/* Conference status */}
          {conferenceStatus !== "idle" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium",
                conferenceStatus === "running" &&
                  "bg-accent-primary/10 text-accent-primary border border-accent-primary/30",
                conferenceStatus === "complete" &&
                  "bg-green-500/10 text-green-400 border border-green-500/30",
                conferenceStatus === "error" &&
                  "bg-red-500/10 text-red-400 border border-red-500/30"
              )}
            >
              {conferenceStatus === "running" && (
                <>
                  <span className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
                  Running
                </>
              )}
              {conferenceStatus === "complete" && (
                <>
                  <Check className="w-3 h-3" />
                  Complete
                </>
              )}
              {conferenceStatus === "error" && (
                <>
                  <AlertCircle className="w-3 h-3" />
                  Error
                </>
              )}
            </motion.div>
          )}

          {/* API Key button/input */}
          {showApiKeyInput ? (
            <div className="flex items-center gap-2">
              <Input
                type="password"
                value={tempApiKey}
                onChange={(e) => setTempApiKey(e.target.value)}
                placeholder="OpenRouter API Key"
                className="w-64 h-8 text-xs"
              />
              <Button size="sm" onClick={handleSaveApiKey}>
                Save
              </Button>
              {apiKey && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowApiKeyInput(false)}
                >
                  Cancel
                </Button>
              )}
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowApiKeyInput(true)}
              className="text-slate-400"
            >
              <Key className="w-4 h-4 mr-2" />
              {apiKey ? "Change API Key" : "Set API Key"}
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}

