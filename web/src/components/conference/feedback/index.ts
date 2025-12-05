// Real-Time Feedback System Components
// Mission Control for Medicine - "Never leave the user wondering what's happening"

export { 
  ActivityFeed, 
  ActivityEventRow, 
  createActivityEvent,
  type ActivityEvent,
  type ActivityEventType,
} from "./ActivityFeed";

export { 
  MasterProgressBar, 
  DEFAULT_V2_PHASES,
  calculateOverallProgress,
  estimateTimeRemaining,
  type Phase,
  type PhaseStatus,
} from "./MasterProgressBar";

export { 
  AgentProgressCard,
  LaneProgressComparison,
  type AgentStatus,
  type AgentRole,
} from "./AgentProgressCard";

export { 
  ConferenceCompleteSummary,
  DEMO_PHASE_BREAKDOWN,
} from "./ConferenceCompleteSummary";

