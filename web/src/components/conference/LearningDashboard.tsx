"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  Lightbulb,
  Sparkles,
  TrendingUp,
  Trash2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Database,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Eye,
  Filter,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// ============================================================================
// TYPES
// ============================================================================

interface Heuristic {
  id: string;
  query_template: string;
  category: string;
  heuristic: string;
  confidence: number;
  success_rate: number;
  times_used: number;
  source_conference?: string;
  created_at?: string;
}

interface Speculation {
  id: string;
  hypothesis: string;
  mechanism: string;
  evidence_level: string;
  source_conference?: string;
  lane: string;
  status: string;
  watch_keywords: string[];
  created_at?: string;
}

interface LearningStats {
  total_heuristics: number;
  total_speculations: number;
  categories: Record<string, number>;
  speculation_statuses: Record<string, number>;
  avg_heuristic_confidence: number;
  total_heuristic_uses: number;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchStats(): Promise<LearningStats> {
  const res = await fetch(`${API_BASE}/learning/stats`);
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

async function fetchHeuristics(category?: string): Promise<{ heuristics: Heuristic[]; total: number }> {
  const url = category 
    ? `${API_BASE}/learning/heuristics?category=${encodeURIComponent(category)}&limit=100`
    : `${API_BASE}/learning/heuristics?limit=100`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch heuristics");
  return res.json();
}

async function fetchSpeculations(status?: string): Promise<{ speculations: Speculation[]; total: number }> {
  const url = status 
    ? `${API_BASE}/learning/speculations?status=${encodeURIComponent(status)}&limit=100`
    : `${API_BASE}/learning/speculations?limit=100`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch speculations");
  return res.json();
}

async function deleteHeuristic(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/learning/heuristics/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete heuristic");
}

async function deleteSpeculation(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/learning/speculations/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete speculation");
}

// ============================================================================
// STAT CARD
// ============================================================================

interface StatCardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
  subtext?: string;
}

function StatCard({ icon: Icon, label, value, color, subtext }: StatCardProps) {
  return (
    <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
      <div className="flex items-center gap-3">
        <div className={cn("p-2 rounded-lg", color)}>
          <Icon className="w-4 h-4 text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-slate-100">{value}</p>
          <p className="text-xs text-slate-400">{label}</p>
          {subtext && <p className="text-[10px] text-slate-500">{subtext}</p>}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// HEURISTIC CARD
// ============================================================================

interface HeuristicCardProps {
  heuristic: Heuristic;
  onDelete: (id: string) => void;
}

function HeuristicCard({ heuristic, onDelete }: HeuristicCardProps) {
  const [expanded, setExpanded] = useState(false);
  
  const categoryColors: Record<string, string> = {
    therapeutic: "bg-green-500/20 text-green-300 border-green-500/30",
    diagnostic: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    prognostic: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    general: "bg-slate-500/20 text-slate-300 border-slate-500/30",
    pharmacology: "bg-purple-500/20 text-purple-300 border-purple-500/30",
    surgery: "bg-red-500/20 text-red-300 border-red-500/30",
  };
  
  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 overflow-hidden">
      <div 
        className="p-3 cursor-pointer hover:bg-slate-700/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Lightbulb className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              <Badge className={cn("text-[10px]", categoryColors[heuristic.category] || categoryColors.general)}>
                {heuristic.category}
              </Badge>
              <span className="text-[10px] text-slate-500">
                {(heuristic.confidence * 100).toFixed(0)}% confidence
              </span>
            </div>
            <p className="text-sm text-slate-200 line-clamp-2">{heuristic.heuristic}</p>
          </div>
          <div className="flex items-center gap-2">
            {heuristic.times_used > 0 && (
              <Badge className="text-[10px] bg-cyan-500/20 text-cyan-300 border-cyan-500/30">
                Used {heuristic.times_used}x
              </Badge>
            )}
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </div>
      </div>
      
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <div className="px-3 pb-3 space-y-2 border-t border-slate-700/50 pt-2">
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">Query Template</span>
                <p className="text-xs text-slate-400 mt-0.5">{heuristic.query_template}</p>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-[10px] text-slate-500">
                  <span>Success rate: {(heuristic.success_rate * 100).toFixed(0)}%</span>
                  {heuristic.created_at && (
                    <span suppressHydrationWarning>Created: {new Date(heuristic.created_at).toLocaleDateString()}</span>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(heuristic.id);
                  }}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ============================================================================
// SPECULATION CARD
// ============================================================================

interface SpeculationCardProps {
  speculation: Speculation;
  onDelete: (id: string) => void;
}

function SpeculationCard({ speculation, onDelete }: SpeculationCardProps) {
  const [expanded, setExpanded] = useState(false);
  
  const statusConfig: Record<string, { color: string; icon: React.ElementType }> = {
    active: { color: "bg-purple-500/20 text-purple-300 border-purple-500/30", icon: Eye },
    promoted: { color: "bg-green-500/20 text-green-300 border-green-500/30", icon: CheckCircle2 },
    deprecated: { color: "bg-red-500/20 text-red-300 border-red-500/30", icon: AlertTriangle },
    watching: { color: "bg-amber-500/20 text-amber-300 border-amber-500/30", icon: Activity },
  };
  
  const config = statusConfig[speculation.status] || statusConfig.active;
  const StatusIcon = config.icon;
  
  return (
    <div className="bg-slate-800/50 rounded-lg border border-purple-500/30 overflow-hidden">
      <div 
        className="p-3 cursor-pointer hover:bg-purple-900/20 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />
              <Badge className={cn("text-[10px]", config.color)}>
                <StatusIcon className="w-2.5 h-2.5 mr-1" />
                {speculation.status}
              </Badge>
              <Badge className="text-[10px] bg-slate-500/20 text-slate-300 border-slate-500/30">
                {speculation.evidence_level}
              </Badge>
            </div>
            <p className="text-sm text-slate-200 line-clamp-2">{speculation.hypothesis}</p>
          </div>
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </div>
      </div>
      
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <div className="px-3 pb-3 space-y-2 border-t border-purple-500/20 pt-2">
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">Mechanism</span>
                <p className="text-xs text-slate-400 mt-0.5">{speculation.mechanism}</p>
              </div>
              {speculation.watch_keywords.length > 0 && (
                <div>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider">Watch Keywords</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {speculation.watch_keywords.map((kw, i) => (
                      <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-[10px] text-slate-500">
                  {speculation.created_at && (
                    <span suppressHydrationWarning>Created: {new Date(speculation.created_at).toLocaleDateString()}</span>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(speculation.id);
                  }}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

interface LearningDashboardProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export function LearningDashboard({ collapsed = true, onToggle }: LearningDashboardProps) {
  const [stats, setStats] = useState<LearningStats | null>(null);
  const [heuristics, setHeuristics] = useState<Heuristic[]>([]);
  const [speculations, setSpeculations] = useState<Speculation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"heuristics" | "speculations">("heuristics");
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, heuristicsData, speculationsData] = await Promise.all([
        fetchStats(),
        fetchHeuristics(categoryFilter),
        fetchSpeculations(statusFilter),
      ]);
      setStats(statsData);
      setHeuristics(heuristicsData.heuristics);
      setSpeculations(speculationsData.speculations);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, statusFilter]);
  
  useEffect(() => {
    if (!collapsed) {
      loadData();
    }
  }, [collapsed, loadData]);
  
  const handleDeleteHeuristic = async (id: string) => {
    try {
      await deleteHeuristic(id);
      setHeuristics(prev => prev.filter(h => h.id !== id));
      if (stats) {
        setStats({ ...stats, total_heuristics: stats.total_heuristics - 1 });
      }
    } catch (e) {
      console.error("Failed to delete heuristic:", e);
    }
  };
  
  const handleDeleteSpeculation = async (id: string) => {
    try {
      await deleteSpeculation(id);
      setSpeculations(prev => prev.filter(s => s.id !== id));
      if (stats) {
        setStats({ ...stats, total_speculations: stats.total_speculations - 1 });
      }
    } catch (e) {
      console.error("Failed to delete speculation:", e);
    }
  };
  
  return (
    <Card className="bg-slate-900/50 border-purple-500/30">
      <CardHeader 
        className="py-3 px-4 cursor-pointer hover:bg-purple-900/20 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400" />
            <CardTitle className="text-base text-purple-300">Learning Dashboard</CardTitle>
            {stats && !collapsed && (
              <div className="flex items-center gap-1 ml-2">
                <Badge className="text-[10px] bg-green-500/20 text-green-300 border-green-500/30">
                  {stats.total_heuristics} heuristics
                </Badge>
                <Badge className="text-[10px] bg-purple-500/20 text-purple-300 border-purple-500/30">
                  {stats.total_speculations} speculations
                </Badge>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!collapsed && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={(e) => {
                  e.stopPropagation();
                  loadData();
                }}
                disabled={loading}
              >
                <RefreshCw className={cn("w-3.5 h-3.5 mr-1", loading && "animate-spin")} />
                Refresh
              </Button>
            )}
            {collapsed ? (
              <ChevronDown className="w-4 h-4 text-purple-400" />
            ) : (
              <ChevronUp className="w-4 h-4 text-purple-400" />
            )}
          </div>
        </div>
      </CardHeader>
      
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <CardContent className="pt-0 space-y-4">
              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}
              
              {/* Stats grid */}
              {stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <StatCard 
                    icon={Database} 
                    label="Heuristics" 
                    value={stats.total_heuristics}
                    color="bg-green-500"
                    subtext={`${stats.avg_heuristic_confidence}% avg confidence`}
                  />
                  <StatCard 
                    icon={Sparkles} 
                    label="Speculations" 
                    value={stats.total_speculations}
                    color="bg-purple-500"
                  />
                  <StatCard 
                    icon={TrendingUp} 
                    label="Total Uses" 
                    value={stats.total_heuristic_uses}
                    color="bg-cyan-500"
                  />
                  <StatCard 
                    icon={Activity} 
                    label="Categories" 
                    value={Object.keys(stats.categories).length}
                    color="bg-amber-500"
                  />
                </div>
              )}
              
              {/* Tabs */}
              <div className="flex items-center gap-2 border-b border-slate-700/50 pb-2">
                <button
                  className={cn(
                    "px-3 py-1.5 text-sm rounded-md transition-colors",
                    activeTab === "heuristics" 
                      ? "bg-green-500/20 text-green-300" 
                      : "text-slate-400 hover:text-slate-200"
                  )}
                  onClick={() => setActiveTab("heuristics")}
                >
                  <Lightbulb className="w-3.5 h-3.5 inline mr-1.5" />
                  Heuristics ({heuristics.length})
                </button>
                <button
                  className={cn(
                    "px-3 py-1.5 text-sm rounded-md transition-colors",
                    activeTab === "speculations" 
                      ? "bg-purple-500/20 text-purple-300" 
                      : "text-slate-400 hover:text-slate-200"
                  )}
                  onClick={() => setActiveTab("speculations")}
                >
                  <Sparkles className="w-3.5 h-3.5 inline mr-1.5" />
                  Speculations ({speculations.length})
                </button>
                
                {/* Filters */}
                <div className="ml-auto flex items-center gap-2">
                  <Filter className="w-3.5 h-3.5 text-slate-400" />
                  {activeTab === "heuristics" && stats && (
                    <select
                      value={categoryFilter || ""}
                      onChange={(e) => setCategoryFilter(e.target.value || undefined)}
                      className="h-7 px-2 text-xs bg-slate-800 border border-slate-700 rounded text-slate-200"
                    >
                      <option value="">All categories</option>
                      {Object.keys(stats.categories).map(cat => (
                        <option key={cat} value={cat}>{cat} ({stats.categories[cat]})</option>
                      ))}
                    </select>
                  )}
                  {activeTab === "speculations" && stats && (
                    <select
                      value={statusFilter || ""}
                      onChange={(e) => setStatusFilter(e.target.value || undefined)}
                      className="h-7 px-2 text-xs bg-slate-800 border border-slate-700 rounded text-slate-200"
                    >
                      <option value="">All statuses</option>
                      {Object.keys(stats.speculation_statuses).map(status => (
                        <option key={status} value={status}>{status} ({stats.speculation_statuses[status]})</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
              
              {/* Content */}
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {loading ? (
                  <div className="py-8 text-center">
                    <RefreshCw className="w-6 h-6 text-purple-400 animate-spin mx-auto mb-2" />
                    <p className="text-sm text-slate-400">Loading...</p>
                  </div>
                ) : activeTab === "heuristics" ? (
                  heuristics.length > 0 ? (
                    heuristics.map(h => (
                      <HeuristicCard key={h.id} heuristic={h} onDelete={handleDeleteHeuristic} />
                    ))
                  ) : (
                    <div className="py-8 text-center">
                      <Database className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                      <p className="text-sm text-slate-400">No heuristics yet</p>
                      <p className="text-xs text-slate-500 mt-1">
                        Heuristics are extracted from successful conferences
                      </p>
                    </div>
                  )
                ) : speculations.length > 0 ? (
                  speculations.map(s => (
                    <SpeculationCard key={s.id} speculation={s} onDelete={handleDeleteSpeculation} />
                  ))
                ) : (
                  <div className="py-8 text-center">
                    <Sparkles className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                    <p className="text-sm text-slate-400">No speculations yet</p>
                    <p className="text-xs text-slate-500 mt-1">
                      Speculations come from Lane B exploratory thinking
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

