"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  History, 
  ChevronDown, 
  ChevronUp, 
  Clock, 
  Trash2, 
  RefreshCw,
  Eye,
  Download,
  GitBranch,
  Layers,
  AlertCircle,
  Check,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  type ConferenceSession, 
  useSessions,
  groupSessionsByDate,
} from "@/lib/sessionStorage";

// ============================================================================
// TYPES
// ============================================================================

interface SessionHistoryPanelProps {
  onSelectSession?: (session: ConferenceSession) => void;
  onRerunSession?: (session: ConferenceSession) => void;
  collapsed?: boolean;
  onToggle?: () => void;
}

// ============================================================================
// SESSION CARD
// ============================================================================

interface SessionCardProps {
  session: ConferenceSession;
  onView?: () => void;
  onRerun?: () => void;
  onDelete?: () => void;
}

function SessionCard({ session, onView, onRerun, onDelete }: SessionCardProps) {
  const [showActions, setShowActions] = useState(false);
  
  const timeStr = session.timestamp.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });

  // Truncate query for display
  const displayQuery = session.query.length > 60 
    ? session.query.substring(0, 60) + "..." 
    : session.query;

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-lg border border-slate-700/50 bg-slate-800/30 overflow-hidden",
        "hover:border-slate-600/50 transition-colors cursor-pointer"
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      onClick={onView}
    >
      <div className="p-3 space-y-2">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-3 h-3 text-slate-500" />
            <span className="text-xs text-slate-400">{timeStr}</span>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Version badge */}
            <Badge className={cn(
              "text-[10px]",
              session.version === "v2.1" 
                ? "bg-cyan-500/20 text-cyan-400" 
                : "bg-slate-500/20 text-slate-400"
            )}>
              {session.version === "v2.1" ? (
                <><GitBranch className="w-2.5 h-2.5 mr-0.5" /> v2.1</>
              ) : (
                <><Layers className="w-2.5 h-2.5 mr-0.5" /> v1</>
              )}
            </Badge>
            
            {/* Status indicator */}
            {session.status === "complete" && (
              <Check className="w-3 h-3 text-green-400" />
            )}
            {session.status === "error" && (
              <AlertCircle className="w-3 h-3 text-red-400" />
            )}
          </div>
        </div>
        
        {/* Query */}
        <p className="text-sm text-slate-200 line-clamp-2">
          {displayQuery}
        </p>
        
        {/* Meta */}
        <div className="flex items-center gap-3 text-[10px] text-slate-500">
          {session.mode && (
            <span>{session.mode}</span>
          )}
          <span>•</span>
          <span>{session.agentCount} agents</span>
          {session.duration && (
            <>
              <span>•</span>
              <span>{(session.duration / 1000).toFixed(1)}s</span>
            </>
          )}
        </div>
        
        {/* Actions (on hover) */}
        <AnimatePresence>
          {showActions && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-2 pt-2 border-t border-slate-700/50"
            >
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => { e.stopPropagation(); onView?.(); }}
                className="flex-1 text-xs"
              >
                <Eye className="w-3 h-3 mr-1" />
                View
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => { e.stopPropagation(); onRerun?.(); }}
                className="flex-1 text-xs"
              >
                <RefreshCw className="w-3 h-3 mr-1" />
                Re-run
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => { e.stopPropagation(); onDelete?.(); }}
                className="text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10"
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ============================================================================
// SESSION GROUP
// ============================================================================

interface SessionGroupProps {
  title: string;
  sessions: ConferenceSession[];
  onView?: (session: ConferenceSession) => void;
  onRerun?: (session: ConferenceSession) => void;
  onDelete?: (session: ConferenceSession) => void;
}

function SessionGroup({ title, sessions, onView, onRerun, onDelete }: SessionGroupProps) {
  return (
    <div className="space-y-2">
      <h4 className="text-xs text-slate-500 uppercase tracking-wider px-1">
        {title}
      </h4>
      <div className="space-y-2">
        {sessions.map((session) => (
          <SessionCard
            key={session.id}
            session={session}
            onView={() => onView?.(session)}
            onRerun={() => onRerun?.(session)}
            onDelete={() => onDelete?.(session)}
          />
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// SESSION HISTORY PANEL
// ============================================================================

export function SessionHistoryPanel({ 
  onSelectSession, 
  onRerunSession,
  collapsed = false,
  onToggle,
}: SessionHistoryPanelProps) {
  const { sessions, loading, error, removeSession, grouped } = useSessions();
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const handleDelete = async (session: ConferenceSession) => {
    if (confirmDelete === session.id) {
      await removeSession(session.id);
      setConfirmDelete(null);
    } else {
      setConfirmDelete(session.id);
      // Auto-reset after 3 seconds
      setTimeout(() => setConfirmDelete(null), 3000);
    }
  };

  const groupOrder = ["Today", "Yesterday", "This Week", "This Month", "Older"];

  return (
    <Card className="bg-slate-800/30 border-slate-700/50">
      <CardHeader
        className={cn(
          "py-3 px-4 border-b border-slate-700/50",
          onToggle && "cursor-pointer hover:bg-slate-800/50 transition-colors"
        )}
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-slate-400" />
            <span className="text-sm font-medium text-slate-200">History</span>
            {sessions.length > 0 && (
              <Badge className="bg-slate-600/50 text-slate-300 text-[10px]">
                {sessions.length}
              </Badge>
            )}
          </div>
          {onToggle && (
            collapsed ? (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            )
          )}
        </div>
      </CardHeader>
      
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <CardContent className="pt-4 max-h-96 overflow-y-auto">
              {loading && (
                <div className="text-center py-8 text-slate-500 text-sm">
                  Loading sessions...
                </div>
              )}
              
              {error && (
                <div className="text-center py-8 text-red-400 text-sm">
                  Failed to load sessions
                </div>
              )}
              
              {!loading && !error && sessions.length === 0 && (
                <div className="text-center py-8 text-slate-500 text-sm">
                  <History className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No conference history</p>
                  <p className="text-xs mt-1">
                    Your past conferences will appear here
                  </p>
                </div>
              )}
              
              {!loading && !error && sessions.length > 0 && (
                <div className="space-y-4">
                  {groupOrder.map((groupName) => {
                    const groupSessions = grouped[groupName];
                    if (!groupSessions || groupSessions.length === 0) return null;
                    
                    return (
                      <SessionGroup
                        key={groupName}
                        title={groupName}
                        sessions={groupSessions}
                        onView={onSelectSession}
                        onRerun={onRerunSession}
                        onDelete={handleDelete}
                      />
                    );
                  })}
                </div>
              )}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// ============================================================================
// EXPORT UTILITIES
// ============================================================================

export function exportSessionAsJSON(session: ConferenceSession): void {
  const data = JSON.stringify(session, null, 2);
  const blob = new Blob([data], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `conference-${session.id}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

