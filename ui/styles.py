"""
CSS styles for the AI Case Conference UI.

This module contains all the CSS styling used by the Streamlit application,
organized as a single constant for easy maintenance and theming.
"""

STYLES = """
<style>
    /* ============================================
       IMPORTS & CSS VARIABLES
       ============================================ */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Source+Sans+3:wght@300;400;500;600;700&display=swap');
    
    :root {
        /* Background Colors */
        --bg-primary: #0f1419;
        --bg-secondary: #1a2332;
        --bg-tertiary: #242f3d;
        --bg-elevated: #2d3a4d;
        
        /* Text Colors */
        --text-primary: #e6edf3;
        --text-secondary: #8b949e;
        --text-muted: #6e7681;
        
        /* Accent Colors */
        --accent-primary: #14b8a6;
        --accent-primary-dim: rgba(20, 184, 166, 0.15);
        --accent-warning: #f59e0b;
        --accent-warning-dim: rgba(245, 158, 11, 0.15);
        --accent-error: #ef4444;
        --accent-error-dim: rgba(239, 68, 68, 0.15);
        --accent-info: #3b82f6;
        --accent-info-dim: rgba(59, 130, 246, 0.15);
        
        /* Agent Colors - refined and professional */
        --agent-advocate: #22c55e;
        --agent-advocate-dim: rgba(34, 197, 94, 0.12);
        --agent-skeptic: #f43f5e;
        --agent-skeptic-dim: rgba(244, 63, 94, 0.12);
        --agent-empiricist: #0ea5e9;
        --agent-empiricist-dim: rgba(14, 165, 233, 0.12);
        --agent-mechanist: #a855f7;
        --agent-mechanist-dim: rgba(168, 85, 247, 0.12);
        --agent-patient: #f97316;
        --agent-patient-dim: rgba(249, 115, 22, 0.12);
        --agent-arbitrator: #64748b;
        --agent-arbitrator-dim: rgba(100, 116, 139, 0.12);
        
        /* Borders & Shadows */
        --border-subtle: rgba(255, 255, 255, 0.06);
        --border-default: rgba(255, 255, 255, 0.1);
        --glow-primary: 0 0 20px rgba(20, 184, 166, 0.15);
        --glow-subtle: 0 4px 20px rgba(0, 0, 0, 0.3);
        
        /* Typography */
        --font-sans: 'Source Sans 3', -apple-system, BlinkMacSystemFont, sans-serif;
        --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
        
        /* Spacing */
        --space-xs: 0.25rem;
        --space-sm: 0.5rem;
        --space-md: 1rem;
        --space-lg: 1.5rem;
        --space-xl: 2rem;
        
        /* Border Radius */
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 16px;
        --radius-xl: 24px;
        
        /* Transitions */
        --transition-fast: 150ms ease;
        --transition-normal: 250ms ease;
        --transition-slow: 400ms ease;
    }
    
    /* ============================================
       BASE STYLES
       ============================================ */
    .stApp {
        font-family: var(--font-sans);
        background: linear-gradient(135deg, var(--bg-primary) 0%, #0d1117 100%);
    }
    
    /* Override Streamlit defaults for dark consistency */
    .stApp > header {
        background: transparent !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
        border-right: 1px solid var(--border-subtle);
    }
    
    section[data-testid="stSidebar"] .stMarkdown h2 {
        font-family: var(--font-sans);
        font-weight: 600;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
        margin-top: var(--space-lg);
        padding-bottom: var(--space-sm);
        border-bottom: 1px solid var(--border-subtle);
    }
    
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-family: var(--font-sans);
        font-weight: 500;
        font-size: 0.85rem;
        color: var(--text-muted);
        margin-top: var(--space-md);
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--bg-tertiary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--bg-elevated);
    }
    
    /* ============================================
       HEADER & BRANDING
       ============================================ */
    .main-header {
        font-family: var(--font-sans);
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--accent-primary) 0%, #0d9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: var(--space-xs);
        letter-spacing: -0.02em;
    }
    
    .sub-header {
        font-family: var(--font-sans);
        font-size: 1rem;
        font-weight: 400;
        color: var(--text-secondary);
        margin-bottom: var(--space-xl);
        letter-spacing: 0.01em;
    }
    
    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        background: var(--accent-primary-dim);
        border: 1px solid rgba(20, 184, 166, 0.3);
        border-radius: 100px;
        font-family: var(--font-mono);
        font-size: 0.75rem;
        color: var(--accent-primary);
    }
    
    .status-dot {
        width: 6px;
        height: 6px;
        background: var(--accent-primary);
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* ============================================
       CARDS & CONTAINERS
       ============================================ */
    .glass-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: var(--space-lg);
        box-shadow: var(--glow-subtle);
        transition: all var(--transition-normal);
    }
    
    .glass-card:hover {
        border-color: var(--border-default);
        box-shadow: var(--glow-primary);
    }
    
    .glass-card-compact {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: var(--space-md);
    }
    
    /* ============================================
       SYNTHESIS & RESULTS BOXES
       ============================================ */
    .synthesis-hero {
        background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
        border: 1px solid var(--accent-primary);
        border-radius: var(--radius-xl);
        padding: var(--space-xl);
        position: relative;
        overflow: hidden;
        box-shadow: var(--glow-primary);
    }
    
    .synthesis-hero::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--accent-primary), #0d9488, var(--accent-primary));
    }
    
    .synthesis-hero h3 {
        font-family: var(--font-sans);
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--accent-primary);
        margin: 0 0 var(--space-md) 0;
    }
    
    .synthesis-hero .content {
        font-family: var(--font-sans);
        font-size: 1.1rem;
        line-height: 1.7;
        color: var(--text-primary);
    }
    
    .confidence-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: var(--accent-primary-dim);
        border: 1px solid rgba(20, 184, 166, 0.3);
        border-radius: var(--radius-md);
        font-family: var(--font-mono);
        font-size: 0.9rem;
        font-weight: 500;
        color: var(--accent-primary);
        margin-top: var(--space-md);
    }
    
    .synthesis-box {
        background: var(--accent-primary-dim);
        border-left: 4px solid var(--accent-primary);
        padding: var(--space-lg);
        border-radius: 0 var(--radius-md) var(--radius-md) 0;
        color: var(--text-primary);
    }
    
    .synthesis-box h3 {
        color: var(--accent-primary);
        font-family: var(--font-sans);
        font-weight: 600;
        margin-top: 0;
    }
    
    .dissent-box {
        background: var(--accent-warning-dim);
        border-left: 4px solid var(--accent-warning);
        padding: var(--space-lg);
        border-radius: 0 var(--radius-md) var(--radius-md) 0;
        color: var(--text-primary);
    }
    
    .dissent-box h4 {
        color: var(--accent-warning);
        font-family: var(--font-sans);
        font-weight: 600;
        margin-top: 0;
    }
    
    /* ============================================
       AGENT CARDS
       ============================================ */
    .agent-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: var(--space-md);
        transition: all var(--transition-normal);
    }
    
    .agent-card:hover {
        border-color: var(--border-default);
        transform: translateY(-2px);
    }
    
    .agent-card.advocate { border-left: 3px solid var(--agent-advocate); }
    .agent-card.skeptic { border-left: 3px solid var(--agent-skeptic); }
    .agent-card.empiricist { border-left: 3px solid var(--agent-empiricist); }
    .agent-card.mechanist { border-left: 3px solid var(--agent-mechanist); }
    .agent-card.patient_voice { border-left: 3px solid var(--agent-patient); }
    
    .agent-header {
        display: flex;
        align-items: center;
        gap: var(--space-sm);
        margin-bottom: var(--space-sm);
    }
    
    .agent-name {
        font-family: var(--font-sans);
        font-weight: 600;
        font-size: 0.95rem;
    }
    
    .agent-name.advocate { color: var(--agent-advocate); }
    .agent-name.skeptic { color: var(--agent-skeptic); }
    .agent-name.empiricist { color: var(--agent-empiricist); }
    .agent-name.mechanist { color: var(--agent-mechanist); }
    .agent-name.patient_voice { color: var(--agent-patient); }
    
    .agent-model {
        font-family: var(--font-mono);
        font-size: 0.75rem;
        color: var(--text-muted);
        background: var(--bg-tertiary);
        padding: 2px 8px;
        border-radius: 4px;
    }
    
    /* ============================================
       PROGRESS & LOADING STATES
       ============================================ */
    .progress-container {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: var(--space-lg);
        position: relative;
        overflow: hidden;
    }
    
    .progress-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
        animation: shimmer 2s infinite;
    }
    
    @keyframes shimmer {
        0% { left: -100%; }
        100% { left: 100%; }
    }
    
    .agent-status-thinking {
        animation: thinking-pulse 1.5s ease-in-out infinite;
    }
    
    @keyframes thinking-pulse {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
    }
    
    /* ============================================
       METRICS & DATA DISPLAY
       ============================================ */
    .metric-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: var(--space-md);
        text-align: center;
        transition: all var(--transition-normal);
    }
    
    .metric-card:hover {
        border-color: var(--accent-primary);
    }
    
    .metric-value {
        font-family: var(--font-mono);
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    .metric-label {
        font-family: var(--font-sans);
        font-size: 0.8rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: var(--space-xs);
    }
    
    /* Confidence meter */
    .confidence-meter {
        width: 100%;
        height: 8px;
        background: var(--bg-tertiary);
        border-radius: 4px;
        overflow: hidden;
        margin-top: var(--space-sm);
    }
    
    .confidence-meter-fill {
        height: 100%;
        border-radius: 4px;
        transition: width var(--transition-slow);
    }
    
    .confidence-meter-fill.high { background: var(--agent-advocate); }
    .confidence-meter-fill.medium { background: var(--accent-warning); }
    .confidence-meter-fill.low { background: var(--accent-error); }
    
    /* ============================================
       BUTTONS & INTERACTIONS
       ============================================ */
    .stButton > button {
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        border-radius: var(--radius-md) !important;
        transition: all var(--transition-fast) !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent-primary) 0%, #0d9488 100%) !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(20, 184, 166, 0.25) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(20, 184, 166, 0.35) !important;
    }
    
    /* ============================================
       TEXT AREA & INPUTS
       ============================================ */
    .stTextArea textarea {
        font-family: var(--font-sans) !important;
        font-size: 0.95rem !important;
        line-height: 1.5 !important;
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
        transition: all var(--transition-fast) !important;
        padding: 0.75rem !important;
    }
    
    .stTextArea textarea::placeholder {
        color: var(--text-muted) !important;
        font-size: 0.9rem !important;
    }
    
    .stTextArea textarea:focus {
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 2px var(--accent-primary-dim) !important;
        outline: none !important;
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div {
        background: var(--bg-secondary) !important;
        border-color: var(--border-subtle) !important;
        font-size: 0.85rem !important;
    }
    
    /* ============================================
       EXPANDERS
       ============================================ */
    .streamlit-expanderHeader {
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        background: var(--bg-secondary) !important;
        border-radius: var(--radius-md) !important;
    }
    
    .streamlit-expanderContent {
        background: var(--bg-secondary) !important;
        border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
    }
    
    /* ============================================
       TABLES
       ============================================ */
    .stMarkdown table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
        overflow: hidden;
    }
    
    .stMarkdown th {
        background: var(--bg-tertiary);
        font-family: var(--font-sans);
        font-weight: 600;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
        padding: var(--space-sm) var(--space-md);
        text-align: left;
    }
    
    .stMarkdown td {
        font-family: var(--font-sans);
        padding: var(--space-sm) var(--space-md);
        border-top: 1px solid var(--border-subtle);
    }
    
    .stMarkdown code {
        font-family: var(--font-mono);
        background: var(--bg-tertiary);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.85em;
    }
    
    /* ============================================
       STAGGERED ANIMATION REVEALS
       ============================================ */
    @keyframes fadeSlideIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .reveal-1 { animation: fadeSlideIn 0.4s ease forwards; animation-delay: 0.1s; opacity: 0; }
    .reveal-2 { animation: fadeSlideIn 0.4s ease forwards; animation-delay: 0.2s; opacity: 0; }
    .reveal-3 { animation: fadeSlideIn 0.4s ease forwards; animation-delay: 0.3s; opacity: 0; }
    .reveal-4 { animation: fadeSlideIn 0.4s ease forwards; animation-delay: 0.4s; opacity: 0; }
    
    /* ============================================
       UTILITY CLASSES
       ============================================ */
    .text-mono { font-family: var(--font-mono); }
    .text-muted { color: var(--text-secondary); }
    .text-small { font-size: 0.85rem; }
    .mt-md { margin-top: var(--space-md); }
    .mb-md { margin-bottom: var(--space-md); }
    .p-md { padding: var(--space-md); }
</style>
"""

