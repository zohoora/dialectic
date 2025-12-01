"""
Streamlit UI for AI Case Conference System.

This provides a web interface for running case conferences with
multiple AI agents deliberating on clinical questions.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from dotenv import load_dotenv

from src.conference.engine import ConferenceEngine, create_default_config, ProgressStage, ProgressUpdate
from src.grounding.engine import GroundingEngine
from src.learning.gatekeeper import Gatekeeper
from src.learning.library import ExperienceLibrary
from src.learning.surgeon import Surgeon
from src.llm.client import LLMClient
from src.models.conference import (
    AgentConfig,
    AgentRole,
    ArbitratorConfig,
    ConferenceConfig,
    ConferenceResult,
)
from src.models.experience import InjectionContext, InjectionResult, ReasoningArtifact
from src.models.feedback import QueryClassification
from src.models.fragility import FragilityOutcome, FragilityReport
from src.models.gatekeeper import GatekeeperOutput, RejectionCode
from src.models.grounding import GroundingReport
from src.learning.classifier import ClassifiedQuery, QueryClassifier
from src.learning.injector import HeuristicInjector
from src.learning.optimizer import ConfigurationOptimizer, FeedbackCollector
from src.shadow.runner import ShadowRunner

# Load environment variables
load_dotenv()


def get_api_key() -> str | None:
    """
    Get OpenRouter API key from Streamlit secrets (cloud) or environment variable (local).
    
    Priority:
    1. Streamlit secrets (for Streamlit Cloud deployment)
    2. Environment variable (for local development)
    """
    # Try Streamlit secrets first (for Streamlit Cloud)
    try:
        return st.secrets["OPENROUTER_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass
    
    # Fall back to environment variable (for local development)
    return os.getenv("OPENROUTER_API_KEY")

# Page configuration
st.set_page_config(
    page_title="AI Case Conference",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Comprehensive CSS Design System
st.markdown("""
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
""", unsafe_allow_html=True)


# Available models on OpenRouter (all thinking/reasoning models)
# These are the exact models specified by user
AVAILABLE_MODELS = {
    # Anthropic
    "🧠 Claude Opus 4.5": "anthropic/claude-opus-4.5",
    # OpenAI
    "🧠 GPT-5.1": "openai/gpt-5.1",
    # DeepSeek
    "🧠 DeepSeek R1": "deepseek/deepseek-r1",
    # Google
    "🧠 Gemini 3 Pro": "google/gemini-3-pro-preview",
    # Alibaba/Qwen
    "🧠 Qwen3-235B Thinking": "qwen/qwen3-235b-a22b-thinking-2507",
    # Moonshot AI
    "🧠 Kimi K2 Thinking": "moonshotai/kimi-k2-thinking",
    # Prime Intellect
    "🧠 Intellect-3": "prime-intellect/intellect-3",
    # xAI
    "🧠 Grok 4": "x-ai/grok-4",
}


def get_role_color(role: str) -> str:
    """Get color for agent role."""
    colors = {
        "advocate": "#4CAF50",
        "skeptic": "#F44336",
        "empiricist": "#2196F3",
        "mechanist": "#9C27B0",
        "patient_voice": "#FF9800",
        "arbitrator": "#607D8B",
    }
    return colors.get(role, "#666666")


def get_role_emoji(role: str) -> str:
    """Get emoji for agent role."""
    emojis = {
        "advocate": "🟢",
        "skeptic": "🔴",
        "empiricist": "🔵",
        "mechanist": "🟣",
        "patient_voice": "🟠",
        "arbitrator": "⚖️",
    }
    return emojis.get(role, "⚪")


def render_sidebar():
    """Render the configuration sidebar with collapsible sections."""
    
    # Quick presets at top
    # Preset buttons - compact
    st.sidebar.caption("PRESETS")
    preset_cols = st.sidebar.columns(3)
    
    # Initialize preset state
    if "preset" not in st.session_state:
        st.session_state.preset = None
    
    with preset_cols[0]:
        if st.button("Fast", use_container_width=True, help="1 round, no verification"):
            st.session_state.preset = "fast"
    with preset_cols[1]:
        if st.button("Standard", use_container_width=True, help="2 rounds, all features"):
            st.session_state.preset = "balanced"
    with preset_cols[2]:
        if st.button("Deep", use_container_width=True, help="3 rounds, thorough"):
            st.session_state.preset = "deep"
    
    # Apply preset defaults
    preset = st.session_state.preset or "balanced"
    preset_config = {
        "fast": {"rounds": 1, "grounding": False, "fragility": False, "frag_tests": 2},
        "balanced": {"rounds": 2, "grounding": True, "fragility": True, "frag_tests": 3},
        "deep": {"rounds": 3, "grounding": True, "fragility": True, "frag_tests": 5},
    }[preset]
    
    st.sidebar.markdown("---")
    
    # Agent Panel
    with st.sidebar.expander("👥 **Agents**", expanded=True):
        st.caption("Select participating agents (min. 2)")
        
        # Agent toggles with model selection inline
        use_advocate = st.checkbox("🟢 Advocate", value=True, help="Builds strongest case")
        if use_advocate:
            advocate_model = st.selectbox(
                "Model", options=list(AVAILABLE_MODELS.keys()), 
                index=1, key="adv_model", label_visibility="collapsed"
            )
        else:
            advocate_model = None
            
        use_skeptic = st.checkbox("🔴 Skeptic", value=True, help="Challenges consensus")
        if use_skeptic:
            skeptic_model = st.selectbox(
                "Model", options=list(AVAILABLE_MODELS.keys()),
                index=2, key="skep_model", label_visibility="collapsed"
            )
        else:
            skeptic_model = None
            
        use_empiricist = st.checkbox("🔵 Empiricist", value=True, help="Grounds in evidence")
        if use_empiricist:
            empiricist_model = st.selectbox(
                "Model", options=list(AVAILABLE_MODELS.keys()),
                index=3, key="emp_model", label_visibility="collapsed"
            )
        else:
            empiricist_model = None
        
        st.markdown("---")
        st.caption("Additional agents")
        
        use_mechanist = st.checkbox("🟣 Mechanist", value=False, help="Biological plausibility")
        if use_mechanist:
            mechanist_model = st.selectbox(
                "Model", options=list(AVAILABLE_MODELS.keys()),
                index=4, key="mech_model", label_visibility="collapsed"
            )
        else:
            mechanist_model = None
            
        use_patient_voice = st.checkbox("🟠 Patient Voice", value=False, help="Patient perspective")
        if use_patient_voice:
            patient_voice_model = st.selectbox(
                "Model", options=list(AVAILABLE_MODELS.keys()),
                index=5, key="pv_model", label_visibility="collapsed"
            )
        else:
            patient_voice_model = None
    
    # Arbitrator
    with st.sidebar.expander("⚖️ **Arbitrator**", expanded=False):
        arbitrator_model = st.selectbox(
            "Synthesis Model",
            options=list(AVAILABLE_MODELS.keys()),
            index=0,
            help="Synthesizes discussion into recommendation",
        )
    
    # Conference Settings
    with st.sidebar.expander("⚙️ **Conference**", expanded=False):
        TOPOLOGY_OPTIONS = {
            "🗣️ Free Discussion": "free_discussion",
            "⚔️ Oxford Debate": "oxford_debate",
            "🎭 Delphi (Anonymous)": "delphi_method",
            "❓ Socratic Spiral": "socratic_spiral",
            "🔴🔵 Red/Blue Team": "red_team_blue_team",
        }
        
        TOPOLOGY_DESCRIPTIONS = {
            "free_discussion": "All agents respond freely",
            "oxford_debate": "Structured debate format",
            "delphi_method": "Anonymous to reduce bias",
            "socratic_spiral": "Questions first, then answers",
            "red_team_blue_team": "Adversarial review",
        }
        
        selected_topology = st.selectbox(
            "Topology",
            options=list(TOPOLOGY_OPTIONS.keys()),
            index=0,
        )
        topology = TOPOLOGY_OPTIONS[selected_topology]
        st.caption(f"ℹ️ {TOPOLOGY_DESCRIPTIONS[topology]}")
        
        num_rounds = st.slider(
            "Rounds",
            min_value=2 if topology in ["oxford_debate", "delphi_method"] else 1,
            max_value=5,
            value=preset_config["rounds"],
        )
    
    # Quality Controls
    with st.sidebar.expander("🔬 **Quality**", expanded=False):
        enable_grounding = st.toggle(
            "Citation Verification",
            value=preset_config["grounding"],
            help="Verify citations against PubMed",
        )
        
        enable_fragility = st.toggle(
            "Fragility Testing",
            value=preset_config["fragility"],
            help="Stress-test recommendation",
        )
        
        if enable_fragility:
            fragility_tests = st.slider(
                "Perturbation Tests",
                min_value=1, max_value=6,
                value=preset_config["frag_tests"],
            )
        else:
            fragility_tests = 3
        
        enable_learning = st.toggle(
            "Experience Library",
            value=True,
            help="Extract learnings for future use",
        )
    
    # Build active agents dict
    active_agents = {}
    if use_advocate and advocate_model:
        active_agents["advocate"] = AVAILABLE_MODELS[advocate_model]
    if use_skeptic and skeptic_model:
        active_agents["skeptic"] = AVAILABLE_MODELS[skeptic_model]
    if use_empiricist and empiricist_model:
        active_agents["empiricist"] = AVAILABLE_MODELS[empiricist_model]
    if use_mechanist and mechanist_model:
        active_agents["mechanist"] = AVAILABLE_MODELS[mechanist_model]
    if use_patient_voice and patient_voice_model:
        active_agents["patient_voice"] = AVAILABLE_MODELS[patient_voice_model]
    
    return {
        "active_agents": active_agents,
        "arbitrator_model": AVAILABLE_MODELS[arbitrator_model],
        "topology": topology,
        "num_rounds": num_rounds,
        "enable_grounding": enable_grounding,
        "enable_fragility": enable_fragility,
        "fragility_tests": fragility_tests,
        "enable_learning": enable_learning,
    }


def render_agent_response(response, round_num: int):
    """Render a single agent response."""
    role = response.role
    emoji = get_role_emoji(role)
    color = get_role_color(role)
    
    with st.expander(f"{emoji} **{role.title()}** - Round {round_num}", expanded=False):
        st.markdown(f"**Model:** `{response.model}`")
        st.markdown(f"**Confidence:** {response.confidence:.0%}")
        if response.changed_from_previous:
            st.warning("📝 Position changed from previous round")
        st.markdown("---")
        st.markdown(response.content)


def render_round(round_result, round_num: int):
    """Render a full conference round."""
    st.markdown(f"### Round {round_num}")
    
    cols = st.columns(len(round_result.agent_responses))
    
    for col, (agent_id, response) in zip(cols, round_result.agent_responses.items()):
        with col:
            render_agent_response(response, round_num)


def render_synthesis(synthesis):
    """Render the final synthesis with hero card design."""
    
    # Confidence color class
    conf_pct = synthesis.confidence * 100
    if conf_pct >= 80:
        conf_color = "#22c55e"
        conf_class = "high"
    elif conf_pct >= 60:
        conf_color = "#f59e0b"
        conf_class = "medium"
    else:
        conf_color = "#ef4444"
        conf_class = "low"
    
    # Escape backticks in consensus to prevent markdown code block issues
    consensus_text = synthesis.final_consensus.replace('`', '&#96;')
    
    st.markdown(
        f'<div class="synthesis-hero reveal-1">'
        f'<h3>CONSENSUS RECOMMENDATION</h3>'
        f'<div class="content">{consensus_text}</div>'
        f'<div style="display: flex; align-items: center; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap;">'
        f'<div class="confidence-badge">'
        f'<span style="color: {conf_color};">●</span>'
        f'<span>{synthesis.confidence:.0%} Confidence</span>'
        f'</div>'
        f'<div style="flex: 1; min-width: 200px;">'
        f'<div class="confidence-meter">'
        f'<div class="confidence-meter-fill {conf_class}" style="width: {conf_pct}%;"></div>'
        f'</div></div></div></div>',
        unsafe_allow_html=True
    )
    
    # Key points in columns
    if synthesis.key_points:
        st.markdown("")  # spacing
        st.markdown("**Key Points of Agreement**")
        cols = st.columns(min(len(synthesis.key_points), 3))
        for i, point in enumerate(synthesis.key_points):
            with cols[i % len(cols)]:
                st.markdown(
                    f'<div class="glass-card-compact" style="height: 100%;">'
                    f'<span style="color: var(--accent-primary);">✓</span> {point}'
                    f'</div>',
                    unsafe_allow_html=True
                )
    
    # Caveats with visual distinction
    if synthesis.caveats:
        st.markdown("")  # spacing
        st.markdown("**Important Caveats**")
        for caveat in synthesis.caveats:
            st.markdown(
                f'<div style="background: var(--accent-warning-dim); border-left: 3px solid var(--accent-warning); padding: 0.75rem 1rem; border-radius: 0 6px 6px 0; margin-bottom: 0.5rem;">'
                f'<span style="color: var(--accent-warning);">⚠</span> {caveat}'
                f'</div>',
                unsafe_allow_html=True
            )


def render_dissent(dissent):
    """Render preserved dissent with polished styling."""
    if not dissent.preserved:
        st.markdown(
            '<div class="glass-card reveal-2" style="text-align: center; padding: 2rem;">'
            '<span style="font-size: 2rem;">✓</span>'
            '<p style="color: var(--agent-advocate); margin: 0.5rem 0 0 0; font-weight: 500;">Full Consensus Reached</p>'
            '<p style="color: var(--text-muted); font-size: 0.9rem;">No significant dissent among agents</p>'
            '</div>',
            unsafe_allow_html=True
        )
        return
    
    role_color = get_role_color(dissent.dissenting_role or "")
    emoji = get_role_emoji(dissent.dissenting_role or "")
    
    st.markdown(
        f'<div class="glass-card reveal-2" style="border-left: 4px solid var(--accent-warning);">'
        f'<div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">'
        f'<span style="font-size: 1.2rem;">{emoji}</span>'
        f'<div>'
        f'<h4 style="margin: 0; color: var(--text-primary); font-weight: 600;">Preserved Dissent</h4>'
        f'<span style="color: var(--text-muted); font-size: 0.85rem;">{dissent.dissenting_agent}</span>'
        f'</div>'
        f'<span style="margin-left: auto; padding: 4px 12px; background: var(--accent-warning-dim); border-radius: 100px; font-size: 0.8rem; color: var(--accent-warning);">{dissent.strength}</span>'
        f'</div>'
        f'<p style="color: var(--text-primary); margin-bottom: 0.75rem;"><strong>Summary:</strong> {dissent.summary}</p>'
        f'<p style="color: var(--text-secondary); margin: 0; font-size: 0.95rem;">{dissent.reasoning}</p>'
        f'</div>',
        unsafe_allow_html=True
    )


def render_grounding(grounding_report: GroundingReport):
    """Render grounding/citation verification results with visual meters."""
    
    if grounding_report is None:
        st.markdown(
            '<div class="glass-card reveal-3" style="text-align: center; opacity: 0.6;">'
            '<span style="color: var(--text-muted);">Citation verification was not enabled</span>'
            '</div>',
            unsafe_allow_html=True
        )
        return
    
    if grounding_report.total_citations == 0:
        st.markdown(
            '<div class="glass-card reveal-3" style="text-align: center;">'
            '<span style="color: var(--text-muted);">No citations found in agent responses</span>'
            '</div>',
            unsafe_allow_html=True
        )
        return
    
    verified_count = len(grounding_report.citations_verified)
    failed_count = len(grounding_report.citations_failed)
    total = grounding_report.total_citations
    verified_pct = (verified_count / total * 100) if total > 0 else 0
    hallucination_pct = grounding_report.hallucination_rate * 100
    
    # Determine color based on rate
    if hallucination_pct <= 10:
        status_color = "#22c55e"
        status_text = "Excellent"
    elif hallucination_pct <= 20:
        status_color = "#f59e0b"
        status_text = "Fair"
    else:
        status_color = "#ef4444"
        status_text = "Concerning"
    
    # Compute rgba for status background
    rgb_values = ",".join(str(int(status_color[i:i+2], 16)) for i in (1, 3, 5))
    
    st.markdown(
        f'<div class="glass-card reveal-3">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">'
        f'<h4 style="margin: 0; color: var(--text-primary);">🔬 Citation Verification</h4>'
        f'<span style="padding: 4px 12px; background: rgba({rgb_values}, 0.15); border-radius: 100px; font-size: 0.8rem; color: {status_color};">{status_text}</span>'
        f'</div>'
        f'<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; text-align: center;">'
        f'<div><div style="font-size: 1.5rem; font-weight: 600; color: var(--text-primary);">{total}</div><div style="font-size: 0.8rem; color: var(--text-muted);">Found</div></div>'
        f'<div><div style="font-size: 1.5rem; font-weight: 600; color: var(--agent-advocate);">{verified_count}</div><div style="font-size: 0.8rem; color: var(--text-muted);">Verified</div></div>'
        f'<div><div style="font-size: 1.5rem; font-weight: 600; color: {status_color};">{hallucination_pct:.0f}%</div><div style="font-size: 0.8rem; color: var(--text-muted);">Hallucination</div></div>'
        f'</div>'
        f'<div style="margin-top: 1rem;">'
        f'<div style="display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--bg-tertiary);">'
        f'<div style="width: {verified_pct}%; background: var(--agent-advocate);"></div>'
        f'<div style="width: {100-verified_pct}%; background: var(--accent-error);"></div>'
        f'</div>'
        f'<div style="display: flex; justify-content: space-between; margin-top: 0.25rem; font-size: 0.75rem; color: var(--text-muted);">'
        f'<span>Verified: {verified_count}</span><span>Failed: {failed_count}</span>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )
    
    # Verified citations
    if grounding_report.citations_verified:
        with st.expander(f"✅ Verified Citations ({len(grounding_report.citations_verified)})", expanded=False):
            for citation in grounding_report.citations_verified:
                st.markdown(f"""
                **Original:** {citation.original_text}
                
                **Title:** {citation.title}
                
                **Authors:** {', '.join(citation.authors[:3])}{'...' if len(citation.authors) > 3 else ''}
                
                **Year:** {citation.year} | **PMID:** [{citation.pmid}](https://pubmed.ncbi.nlm.nih.gov/{citation.pmid}/)
                
                *Match: {citation.match_type} ({citation.match_confidence:.0%} confidence)*
                
                ---
                """)
    
    # Failed citations
    if grounding_report.citations_failed:
        with st.expander(f"❌ Unverified Citations ({len(grounding_report.citations_failed)})", expanded=True):
            for citation in grounding_report.citations_failed:
                st.markdown(f"""
                **Original:** {citation.original_text}
                
                **Reason:** {citation.reason}
                """)
                
                if citation.closest_match:
                    st.markdown(f"""
                    **Closest Match:** {citation.closest_match.title} ({citation.closest_match.year})
                    [PMID: {citation.closest_match.pmid}](https://pubmed.ncbi.nlm.nih.gov/{citation.closest_match.pmid}/)
                    """)
                
                st.markdown("---")


def render_fragility(fragility_report: FragilityReport):
    """Render fragility testing results with visual gauge."""
    
    if fragility_report is None:
        st.markdown(
            '<div class="glass-card reveal-4" style="text-align: center; opacity: 0.6;">'
            '<span style="color: var(--text-muted);">Fragility testing was not enabled</span>'
            '</div>',
            unsafe_allow_html=True
        )
        return
    
    if fragility_report.perturbations_tested == 0:
        st.markdown(
            '<div class="glass-card reveal-4" style="text-align: center;">'
            '<span style="color: var(--text-muted);">No fragility tests were run</span>'
            '</div>',
            unsafe_allow_html=True
        )
        return
    
    survived = len(fragility_report.survived)
    modified = len(fragility_report.modified)
    collapsed = len(fragility_report.collapsed)
    total = fragility_report.perturbations_tested
    survival_pct = fragility_report.survival_rate * 100
    
    # Determine fragility level styling
    level = fragility_report.fragility_level
    if level == "LOW":
        level_color = "#22c55e"
        level_bg = "rgba(34, 197, 94, 0.15)"
    elif level == "MODERATE":
        level_color = "#f59e0b"
        level_bg = "rgba(245, 158, 11, 0.15)"
    else:
        level_color = "#ef4444"
        level_bg = "rgba(239, 68, 68, 0.15)"
    
    # Compute percentages for bars
    survived_pct = survived/total*100 if total else 0
    modified_pct = modified/total*100 if total else 0
    collapsed_pct = collapsed/total*100 if total else 0
    
    st.markdown(
        f'<div class="glass-card reveal-4">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">'
        f'<h4 style="margin: 0; color: var(--text-primary);">🔥 Fragility Testing</h4>'
        f'<span style="padding: 6px 14px; background: {level_bg}; border: 1px solid {level_color}; border-radius: 100px; font-size: 0.85rem; font-weight: 500; color: {level_color};">{level} Fragility</span>'
        f'</div>'
        f'<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; text-align: center; margin-bottom: 1rem;">'
        f'<div class="glass-card-compact"><div style="font-size: 1.25rem; font-weight: 600; color: var(--text-primary);">{total}</div><div style="font-size: 0.75rem; color: var(--text-muted);">Tests</div></div>'
        f'<div class="glass-card-compact"><div style="font-size: 1.25rem; font-weight: 600; color: var(--agent-advocate);">{survived}</div><div style="font-size: 0.75rem; color: var(--text-muted);">Survived</div></div>'
        f'<div class="glass-card-compact"><div style="font-size: 1.25rem; font-weight: 600; color: var(--accent-warning);">{modified}</div><div style="font-size: 0.75rem; color: var(--text-muted);">Modified</div></div>'
        f'<div class="glass-card-compact"><div style="font-size: 1.25rem; font-weight: 600; color: var(--accent-error);">{collapsed}</div><div style="font-size: 0.75rem; color: var(--text-muted);">Collapsed</div></div>'
        f'</div>'
        f'<div><div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">'
        f'<span style="font-size: 0.85rem; color: var(--text-secondary);">Survival Rate</span>'
        f'<span style="font-size: 0.85rem; font-weight: 600; color: {level_color};">{survival_pct:.0f}%</span></div>'
        f'<div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden; background: var(--bg-tertiary);">'
        f'<div style="width: {survived_pct}%; background: var(--agent-advocate);"></div>'
        f'<div style="width: {modified_pct}%; background: var(--accent-warning);"></div>'
        f'<div style="width: {collapsed_pct}%; background: var(--accent-error);"></div>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )
    
    # Detailed results
    for result in fragility_report.results:
        outcome = result.outcome
        
        # Choose color/icon based on outcome
        if outcome == FragilityOutcome.SURVIVES:
            icon = "✅"
            color = "success"
        elif outcome == FragilityOutcome.MODIFIES:
            icon = "⚠️"
            color = "warning"
        else:  # COLLAPSES
            icon = "❌"
            color = "error"
        
        with st.expander(f"{icon} {result.perturbation}", expanded=(outcome != FragilityOutcome.SURVIVES)):
            st.markdown(f"**Outcome:** `{outcome.value}`")
            st.markdown(f"**Explanation:** {result.explanation}")
            
            if result.modified_recommendation:
                st.markdown("**Modified Recommendation:**")
                st.info(result.modified_recommendation)


def render_metrics(result: ConferenceResult):
    """Render conference metrics with polished styling."""
    
    tokens = result.token_usage.total_tokens
    cost = result.token_usage.estimated_cost_usd
    duration = result.duration_ms / 1000
    rounds = len(result.rounds)
    
    st.markdown(
        f'<div class="glass-card" style="margin-top: 2rem;">'
        f'<h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-weight: 600;">📊 Conference Metrics</h4>'
        f'<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; text-align: center;">'
        f'<div><div style="font-family: var(--font-mono); font-size: 1.25rem; font-weight: 600; color: var(--accent-primary);">{tokens:,}</div>'
        f'<div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Tokens</div></div>'
        f'<div><div style="font-family: var(--font-mono); font-size: 1.25rem; font-weight: 600; color: var(--text-primary);">${cost:.4f}</div>'
        f'<div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Est. Cost</div></div>'
        f'<div><div style="font-family: var(--font-mono); font-size: 1.25rem; font-weight: 600; color: var(--text-primary);">{duration:.1f}s</div>'
        f'<div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Duration</div></div>'
        f'<div><div style="font-family: var(--font-mono); font-size: 1.25rem; font-weight: 600; color: var(--text-primary);">{rounds}</div>'
        f'<div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Rounds</div></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )


def render_gatekeeper(gk_output: GatekeeperOutput, result: ConferenceResult):
    """Render Gatekeeper evaluation results."""
    st.markdown("## 🚪 Gatekeeper Evaluation")
    
    if gk_output is None:
        st.info("Gatekeeper evaluation was not enabled for this conference.")
        return
    
    # Summary
    cols = st.columns(3)
    
    with cols[0]:
        if gk_output.eligible:
            st.success("✅ **Eligible** for Experience Library")
        else:
            st.error(f"❌ **Rejected**: {gk_output.rejection_code.value if gk_output.rejection_code else 'Unknown'}")
    
    with cols[1]:
        st.metric("Confidence", f"{gk_output.confidence:.0%}")
    
    with cols[2]:
        if gk_output.flags:
            flags_str = ", ".join(f.value for f in gk_output.flags)
            st.info(f"Flags: {flags_str}")
        else:
            st.info("No flags")
    
    # Reason
    st.markdown(f"**Reason:** {gk_output.reason}")
    
    # Show extraction option if eligible
    if gk_output.eligible:
        st.markdown("---")
        st.markdown("### 📝 Extract Heuristic")
        st.markdown(
            "This conference result meets quality criteria for extraction. "
            "The heuristic will be saved to the Experience Library for future reference."
        )
        
        if st.button("🔬 Extract Heuristic", key="extract_btn"):
            st.session_state["extract_requested"] = True
            st.rerun()


def render_extraction_result(extraction_success: bool, artifact=None, failure_reason=None):
    """Render heuristic extraction result."""
    st.markdown("## 📚 Heuristic Extraction")
    
    if extraction_success and artifact:
        st.success("✅ Heuristic successfully extracted!")
        
        with st.expander("View Extracted Heuristic", expanded=True):
            st.markdown(f"**ID:** `{artifact.heuristic_id}`")
            st.markdown(f"**Domain:** {artifact.context_vector.domain}")
            st.markdown(f"**Condition:** {artifact.context_vector.condition}")
            st.markdown("---")
            st.markdown(f"**Heuristic:** {artifact.winning_heuristic}")
            
            if artifact.contra_heuristic:
                st.markdown(f"**Counter-argument:** {artifact.contra_heuristic}")
            
            if artifact.qualifying_conditions:
                st.markdown("**Qualifying Conditions:**")
                for cond in artifact.qualifying_conditions:
                    st.markdown(f"- {cond}")
            
            if artifact.disqualifying_conditions:
                st.markdown("**Disqualifying Conditions:**")
                for cond in artifact.disqualifying_conditions:
                    st.markdown(f"- {cond}")
            
            st.markdown(f"**Confidence:** {artifact.confidence:.0%}")
    else:
        st.warning(f"❌ Extraction failed: {failure_reason or 'Unknown reason'}")


def render_library_stats(library: ExperienceLibrary):
    """Render Experience Library statistics in sidebar."""
    stats = library.get_stats()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📚 Library Stats")
    st.sidebar.metric("Total Heuristics", stats["total_heuristics"])
    st.sidebar.metric("Active", stats["active_heuristics"])
    
    if stats["domains"]:
        domains_str = ", ".join(f"{d}: {c}" for d, c in list(stats["domains"].items())[:3])
        st.sidebar.caption(f"Domains: {domains_str}")


@st.cache_resource
def get_experience_library() -> ExperienceLibrary:
    """Get the shared Experience Library instance."""
    storage_path = Path(__file__).parent.parent / "data" / "experience_library.json"
    return ExperienceLibrary(storage_path=storage_path)


@st.cache_resource
def get_optimizer() -> ConfigurationOptimizer:
    """Get the shared Configuration Optimizer instance."""
    storage_path = Path(__file__).parent.parent / "data" / "optimizer_state.json"
    return ConfigurationOptimizer(storage_path=storage_path)


@st.cache_resource
def get_feedback_collector() -> FeedbackCollector:
    """Get the shared Feedback Collector instance."""
    storage_path = Path(__file__).parent.parent / "data" / "feedback.json"
    return FeedbackCollector(storage_path=storage_path)


def render_feedback_form(conference_id: str, has_dissent: bool):
    """Render a simplified, polished feedback form."""
    
    st.markdown(
        '<div class="glass-card" style="margin-top: 2rem;">'
        '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">'
        '<h4 style="margin: 0; color: var(--text-primary);">📝 Quick Feedback</h4>'
        '<span style="font-size: 0.8rem; color: var(--text-muted);">Helps improve recommendations</span>'
        '</div></div>',
        unsafe_allow_html=True
    )
    
    with st.form(key=f"feedback_form_{conference_id}"):
        # Simplified rating row
        st.markdown("**Was this consultation helpful?**")
        rating_cols = st.columns(5)
        
        rating_options = [
            ("😔", "Not helpful"),
            ("😕", "Slightly"),
            ("😐", "Somewhat"),
            ("🙂", "Helpful"),
            ("😀", "Very helpful"),
        ]
        
        useful = st.radio(
            "Rating",
            options=["1", "2", "3", "4", "5"],
            format_func=lambda x: rating_options[int(x)-1][0],
            horizontal=True,
            label_visibility="collapsed",
        )
        
        # Action toggle
        st.markdown("")  # spacing
        will_act = st.radio(
            "Will you act on this recommendation?",
            options=["yes", "modified", "no"],
            format_func=lambda x: {"yes": "✓ Will follow", "modified": "↻ With modifications", "no": "✗ Won't follow"}.get(x, x),
            horizontal=True,
        )
        
        dissent_useful = None
        if has_dissent:
            st.markdown("")  # spacing
            dissent_useful = st.checkbox(
                "The dissenting opinion raised important points",
                value=False,
            )
        
        submitted = st.form_submit_button("Submit Feedback", use_container_width=True, type="secondary")
        
        if submitted:
            # Map rating to useful category
            useful_map = {"1": "no", "2": "no", "3": "partially", "4": "yes", "5": "yes"}
            
            collector = get_feedback_collector()
            collector.record_immediate(
                conference_id,
                useful=useful_map.get(useful),
                will_act=will_act,
                dissent_useful=dissent_useful,
            )
            
            # Also update optimizer if we have outcome
            outcome = collector.get_outcome(conference_id)
            if outcome is not None and "last_config" in st.session_state:
                optimizer = get_optimizer()
                query_class = QueryClassification(query_type="general")
                optimizer.update(query_class, st.session_state["last_config"], outcome)
            
            st.markdown(
                '<div style="background: var(--accent-primary-dim); border: 1px solid var(--accent-primary); border-radius: 8px; padding: 1rem; text-align: center; margin-top: 0.5rem;">'
                '<span style="color: var(--accent-primary);">✓ Thank you for your feedback!</span>'
                '</div>',
                unsafe_allow_html=True
            )
            return True
    
    return False


def render_optimizer_insights():
    """Render optimizer insights in sidebar."""
    optimizer = get_optimizer()
    stats = optimizer.get_stats()
    
    if stats["total_observations"] < 5:
        return  # Not enough data yet
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 Optimization Insights")
    st.sidebar.caption(f"Based on {stats['total_observations']} conferences")
    
    insights = optimizer.get_insights("general")
    
    # Show best models if available
    if insights["best_models"]:
        best = insights["best_models"][0]
        if best.effect_size is not None:
            st.sidebar.metric(
                "Best Performing Model",
                best.component_value.split("/")[-1],
                f"{best.effect_size:.0%} avg outcome",
            )


def render_classification(classification: ClassifiedQuery):
    """Render query classification results."""
    st.markdown("## 🏷️ Query Classification")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Type", classification.query_type.replace("_", " ").title())
    with col2:
        st.metric("Domain", classification.domain.title())
    with col3:
        st.metric("Complexity", classification.complexity.title())
    with col4:
        st.metric("Confidence", f"{classification.classification_confidence:.0%}")
    
    if classification.subtags:
        st.markdown(f"**Subtags:** {', '.join(classification.subtags)}")
    
    if classification.uncertainty_domain != "both_known":
        st.info(f"📊 **Uncertainty:** {classification.uncertainty_domain.replace('_', ' ').title()}")


@st.cache_resource
def get_shadow_runner() -> ShadowRunner:
    """Get the shared Shadow Runner instance."""
    from src.llm.client import LLMClient
    from src.conference.engine import ConferenceEngine
    storage_path = Path(__file__).parent.parent / "data" / "shadow_results.json"
    client = LLMClient()
    engine = ConferenceEngine(client)
    return ShadowRunner(client, engine, storage_path=storage_path)


def render_shadow_summary():
    """Render shadow mode summary in sidebar."""
    runner = get_shadow_runner()
    summary = runner.get_summary()
    
    if summary.total_shadow_runs == 0:
        return
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👻 Shadow Mode Stats")
    st.sidebar.caption(f"{summary.total_shadow_runs} shadow runs completed")
    
    if summary.improvements_found > 0:
        st.sidebar.metric(
            "Improvements Found",
            f"{summary.improvement_rate:.0%}",
            f"{summary.improvements_found} better configs",
        )
    
    if summary.best_config_signature:
        st.sidebar.markdown(f"**Best Config:** `{summary.best_config_signature[:25]}...`")


def render_injection_info(injection_result: InjectionResult):
    """Render information about injected heuristics."""
    if injection_result.genesis_mode:
        st.info(
            "🌟 **Genesis Mode**: No relevant heuristics found. "
            "This could become a founding heuristic for this query type!"
        )
        return
    
    if not injection_result.heuristics:
        return
    
    st.markdown("## 🧠 Experience Library Match")
    
    if injection_result.collision:
        st.warning(
            f"⚠️ **Collision Detected**: {injection_result.collision.collision_type.value.replace('_', ' ').title()}\n\n"
            f"*{injection_result.collision.resolution_hint}*"
        )
    
    for i, h in enumerate(injection_result.heuristics):
        with st.expander(
            f"{'Heuristic A' if i == 0 else 'Heuristic B'}: {h.heuristic_id}",
            expanded=i == 0,
        ):
            st.markdown(f"**Confidence:** {h.confidence:.0%}")
            st.markdown(f"**Prior Usage:** Accepted {h.times_accepted}/{h.times_injected} times")
            st.markdown(f"**Heuristic:**")
            st.markdown(f"> {h.winning_heuristic}")
            
            if h.qualifying_conditions:
                st.markdown("**Qualifying Conditions:**")
                for c in h.qualifying_conditions:
                    st.markdown(f"- {c}")
            
            if h.disqualifying_conditions:
                st.markdown("**Disqualifying Conditions:**")
                for c in h.disqualifying_conditions:
                    st.markdown(f"- {c}")
            
            if h.contra_heuristic:
                st.markdown(f"**Counter-argument:** {h.contra_heuristic}")


async def run_conference_async(
    query: str, 
    config: ConferenceConfig,
    enable_grounding: bool = True,
    enable_fragility: bool = True,
    fragility_tests: int = 3,
    progress_callback=None,
) -> ConferenceResult:
    """Run the conference asynchronously."""
    client = LLMClient()
    
    # Create grounding engine if enabled
    grounding_engine = GroundingEngine() if enable_grounding else None
    
    engine = ConferenceEngine(client, grounding_engine=grounding_engine)
    return await engine.run_conference(
        query=query, 
        config=config,
        enable_grounding=enable_grounding,
        enable_fragility=enable_fragility,
        fragility_tests=fragility_tests,
        progress_callback=progress_callback,
    )


def main():
    """Main application."""
    # Check for API key first
    api_key = get_api_key()
    
    # Compact header with status
    status_color = "var(--accent-primary)" if api_key else "#ef4444"
    status_bg = "var(--accent-primary-dim)" if api_key else "rgba(239, 68, 68, 0.15)"
    status_text = "Ready" if api_key else "No API Key"
    
    st.markdown(
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-subtle);">'
        f'<div>'
        f'<h1 style="font-family: var(--font-sans); font-size: 1.5rem; font-weight: 600; color: var(--text-primary); margin: 0; letter-spacing: -0.02em;">Case Conference</h1>'
        f'<p style="font-size: 0.85rem; color: var(--text-muted); margin: 0.25rem 0 0 0;">Multi-agent clinical deliberation</p>'
        f'</div>'
        f'<div style="display: flex; align-items: center; gap: 6px; padding: 4px 10px; background: {status_bg}; border-radius: 4px;">'
        f'<span style="width: 6px; height: 6px; background: {status_color}; border-radius: 50%;"></span>'
        f'<span style="font-size: 0.75rem; color: {status_color}; font-weight: 500;">{status_text}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )
    
    if not api_key:
        st.markdown(
            '<div class="glass-card" style="border-color: var(--accent-error); margin-top: 1rem;">'
            '<h4 style="color: var(--accent-error); margin-top: 0;">⚠️ API Key Required</h4>'
            '<p style="color: var(--text-secondary); margin-bottom: 1rem;">Please configure your OpenRouter API key to start using the conference system.</p>'
            '<div style="display: grid; gap: 1rem; grid-template-columns: 1fr 1fr;">'
            '<div class="glass-card-compact">'
            '<strong style="color: var(--text-primary);">Local Development</strong>'
            '<p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 0.5rem;">Set <code>OPENROUTER_API_KEY</code> environment variable or create a <code>.env</code> file</p>'
            '</div>'
            '<div class="glass-card-compact">'
            '<strong style="color: var(--text-primary);">Streamlit Cloud</strong>'
            '<p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 0.5rem;">Add <code>OPENROUTER_API_KEY</code> in your app\'s Secrets settings</p>'
            '</div></div></div>',
            unsafe_allow_html=True
        )
        st.stop()
    
    # Ensure the environment variable is set for downstream components
    os.environ["OPENROUTER_API_KEY"] = api_key
    
    # Sidebar configuration
    config_options = render_sidebar()
    
    # Show library stats if learning is enabled
    if config_options.get("enable_learning", True):
        library = get_experience_library()
        render_library_stats(library)
        render_optimizer_insights()
        render_shadow_summary()
    
    # Initialize query from session state
    if "query_text" not in st.session_state:
        st.session_state.query_text = ""
    
    # Minimal label
    st.markdown(
        '<p style="color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; '
        'letter-spacing: 0.08em; margin-bottom: 0.5rem;">Enter clinical scenario</p>',
        unsafe_allow_html=True
    )
    
    query = st.text_area(
        "Query",
        value=st.session_state.query_text,
        placeholder="62-year-old male with cold-type CRPS of the right hand, failed gabapentin and physical therapy. What treatment approach would you recommend?",
        height=100,
        label_visibility="collapsed",
    )
    
    # Example chips - subtle inline style
    EXAMPLE_QUERIES = [
        ("CRPS", "62-year-old male with cold-type CRPS of the right hand, failed gabapentin and physical therapy. What treatment approach would you recommend?"),
        ("Drug interaction", "Patient on warfarin needs NSAID for acute gout flare. How should I manage anticoagulation and pain?"),
        ("Depression", "45-year-old with treatment-resistant depression, failed 3 SSRIs and SNRIs. What are the next steps?"),
    ]
    
    st.markdown(
        '<p style="color: var(--text-muted); font-size: 0.75rem; margin: 0.5rem 0 0.25rem 0;">Examples:</p>',
        unsafe_allow_html=True
    )
    example_cols = st.columns(3)
    for col, (label, example_query) in zip(example_cols, EXAMPLE_QUERIES):
        with col:
            if st.button(label, use_container_width=True, key=f"ex_{label}", type="secondary"):
                st.session_state.query_text = example_query
                st.rerun()
    
    st.markdown("")  # Spacing
    
    # Run button
    agent_count = len(config_options["active_agents"])
    run_button = st.button(
        f"Start Conference  →", 
        type="primary", 
        use_container_width=True,
        disabled=agent_count < 2,
    )
    if agent_count < 2:
        st.caption("⚠️ Select at least 2 agents")
    
    if run_button and query:
        # Create configuration
        # Validate minimum agents
        if len(config_options["active_agents"]) < 2:
            st.error("❌ Please select at least 2 agents for the conference.")
            return
        
        config = create_default_config(
            active_agents=config_options["active_agents"],
            arbitrator_model=config_options["arbitrator_model"],
            num_rounds=config_options["num_rounds"],
            topology=config_options["topology"],
        )
        
        # Classify the query
        classifier = QueryClassifier()
        classification = classifier.classify(query)
        
        # Get heuristic injection if learning is enabled
        injection_result = None
        if config_options.get("enable_learning", True):
            library = get_experience_library()
            injector = HeuristicInjector(library)
            injection_result = injector.get_injection_for_query(classification)
        
        # Classification is done but not displayed to keep UI clean
        # (classification is still used for heuristic injection)
        
        # Show injection info if any heuristics matched
        if injection_result:
            st.markdown("---")
            render_injection_info(injection_result)
        
        # Progress display with enhanced styling
        progress_container = st.container()
        
        # Track round state for UI
        round_state = {"current": 1, "total": config_options["num_rounds"], "phase": "deliberation"}
        
        # Get topology display info
        topology_names = {
            "free_discussion": ("Free Discussion", "All agents deliberate openly"),
            "oxford_debate": ("Oxford Debate", "Structured proposition vs opposition"),
            "delphi_method": ("Delphi Method", "Anonymous iterative consensus"),
            "socratic_spiral": ("Socratic Spiral", "Question-driven exploration"),
            "red_team_blue_team": ("Red Team / Blue Team", "Adversarial challenge & defense"),
        }
        topology_name, topology_desc = topology_names.get(
            config_options["topology"], 
            ("Conference", "Multi-agent deliberation")
        )
        
        with progress_container:
            # Header with round indicator
            header_container = st.empty()
            
            def render_header():
                return (
                    f'<div style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 1rem; margin-bottom: 1rem;">'
                    f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">'
                    f'<div>'
                    f'<h3 style="color: var(--text-primary); margin: 0; font-weight: 600; font-size: 1.1rem;">{topology_name}</h3>'
                    f'<p style="color: var(--text-muted); font-size: 0.8rem; margin: 0.25rem 0 0 0;">{topology_desc}</p>'
                    f'</div>'
                    f'<div style="text-align: right;">'
                    f'<div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-primary);">Round {round_state["current"]}<span style="font-size: 1rem; color: var(--text-muted); font-weight: 400;">/{round_state["total"]}</span></div>'
                    f'<div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">{round_state["phase"]}</div>'
                    f'</div>'
                    f'</div>'
                    f'<div style="display: flex; gap: 4px; height: 6px;">'
                    + "".join(
                        f'<div style="flex: 1; background: {"var(--accent-primary)" if i <= round_state["current"] or round_state["phase"] == "Complete" else "var(--bg-tertiary)"}; border-radius: 3px; transition: background 0.3s;"></div>'
                        for i in range(1, round_state["total"] + 1)
                    )
                    + f'</div></div>'
                )
            
            header_container.markdown(render_header(), unsafe_allow_html=True)
            
            # Main progress bar
            progress_bar = st.progress(0)
            
            # Status message
            status_text = st.empty()
            
            # Agent status as styled cards
            agent_status_container = st.empty()
            
            # Initialize agent status tracking (dynamically based on active agents)
            agent_statuses = {}
            for role, model in config_options['active_agents'].items():
                agent_statuses[role] = {
                    "status": "pending", 
                    "model": model.split('/')[-1], 
                    "confidence": None
                }
            
            # Role colors and emojis
            role_colors = {
                "advocate": "#22c55e", "skeptic": "#f43f5e", "empiricist": "#0ea5e9",
                "mechanist": "#a855f7", "patient_voice": "#f97316"
            }
            role_emojis = {
                "advocate": "🟢", "skeptic": "🔴", "empiricist": "🔵",
                "mechanist": "🟣", "patient_voice": "🟠"
            }
            
            # Render agent status as styled cards
            def render_agent_status_cards():
                cards_html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin-top: 1rem;">'
                for role, info in agent_statuses.items():
                    color = role_colors.get(role, "#64748b")
                    emoji = role_emojis.get(role, "⚪")
                    display_name = role.replace("_", " ").title()
                    
                    # Status styling
                    if info['status'] == "thinking":
                        status_html = '<span class="agent-status-thinking" style="color: #f59e0b;">● Thinking...</span>'
                        border_style = f"border-left: 3px solid {color}; opacity: 1;"
                    elif info['status'] == "done":
                        conf = f"{info['confidence']:.0%}" if info['confidence'] else ""
                        status_html = f'<span style="color: #22c55e;">✓ Done {conf}</span>'
                        border_style = f"border-left: 3px solid {color};"
                    else:
                        status_html = '<span style="color: var(--text-muted);">○ Pending</span>'
                        border_style = f"border-left: 3px solid var(--bg-tertiary); opacity: 0.6;"
                    
                    cards_html += f'<div style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 0.75rem; {border_style}"><div style="font-weight: 600; color: {color}; font-size: 0.9rem;">{emoji} {display_name}</div><div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted); margin: 0.25rem 0;">{info["model"]}</div><div style="font-size: 0.8rem;">{status_html}</div></div>'
                cards_html += '</div>'
                return cards_html
            
            agent_status_container.markdown(render_agent_status_cards(), unsafe_allow_html=True)
            
            # Live dialogue/transcript view
            dialogue_container = st.expander("🎙️ Live Dialogue (listen in)", expanded=False)
            dialogue_entries = []
            dialogue_display = dialogue_container.empty()
            
            def add_dialogue_entry(role: str, content: str, round_num: int):
                """Add an agent response to the live dialogue."""
                color = role_colors.get(role, "#64748b")
                emoji = role_emojis.get(role, "⚪")
                display_name = role.replace("_", " ").title()
                # Truncate content for preview but show full on hover
                preview = content[:300] + "..." if len(content) > 300 else content
                dialogue_entries.append({
                    "role": role,
                    "display_name": display_name,
                    "content": content,
                    "preview": preview,
                    "round": round_num,
                    "color": color,
                    "emoji": emoji,
                })
                render_dialogue()
            
            def render_dialogue():
                """Render the dialogue entries."""
                if not dialogue_entries:
                    dialogue_display.markdown(
                        '<p style="color: var(--text-muted); font-style: italic; text-align: center; padding: 1rem;">'
                        'Agent responses will appear here as they complete...</p>',
                        unsafe_allow_html=True
                    )
                    return
                
                html_parts = []
                current_round = 0
                for entry in dialogue_entries:
                    # Add round separator if new round
                    if entry["round"] != current_round:
                        current_round = entry["round"]
                        html_parts.append(
                            f'<div style="text-align: center; margin: 1rem 0; color: var(--text-muted); font-size: 0.8rem;">'
                            f'<span style="background: var(--bg-tertiary); padding: 4px 12px; border-radius: 4px;">Round {current_round}</span></div>'
                        )
                    
                    html_parts.append(
                        f'<div style="background: var(--bg-secondary); border-left: 3px solid {entry["color"]}; '
                        f'border-radius: 0 8px 8px 0; padding: 0.75rem 1rem; margin-bottom: 0.75rem;">'
                        f'<div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">'
                        f'<span style="font-weight: 600; color: {entry["color"]};">{entry["emoji"]} {entry["display_name"]}</span>'
                        f'</div>'
                        f'<div style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; white-space: pre-wrap;">{entry["preview"]}</div>'
                        f'</div>'
                    )
                
                dialogue_display.markdown("".join(html_parts), unsafe_allow_html=True)
            
            render_dialogue()  # Initial empty state
            
            # Activity timeline (more compact)
            log_container = st.expander("📋 Activity Log", expanded=False)
            log_messages = []
            log_display = log_container.empty()
            
            def update_log(message: str):
                """Add a message to the live log with styled timeline."""
                import datetime
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                log_messages.append(
                    f'<div style="display: flex; gap: 0.75rem; padding: 0.25rem 0; '
                    f'border-left: 2px solid var(--bg-tertiary); padding-left: 0.75rem;">'
                    f'<span style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted);">{timestamp}</span>'
                    f'<span style="color: var(--text-secondary); font-size: 0.9rem;">{message}</span></div>'
                )
                # Keep only last 15 messages
                if len(log_messages) > 15:
                    log_messages.pop(0)
                log_display.markdown("\n".join(log_messages), unsafe_allow_html=True)
            
            # Create progress callback
            def progress_callback(update: ProgressUpdate):
                """Handle progress updates from the conference engine."""
                # Update progress bar
                progress_bar.progress(min(update.percent, 100))
                
                # Update status text with styled message
                status_text.markdown(
                    f'<p style="color: var(--text-secondary); font-size: 0.95rem; margin: 0.5rem 0;">{update.message}</p>',
                    unsafe_allow_html=True
                )
                
                # Handle stage-specific updates
                if update.stage == ProgressStage.AGENT_THINKING:
                    # Get role and convert enum to string if needed
                    role_raw = update.detail.get("role", "")
                    role = str(role_raw).lower() if role_raw else ""
                    if hasattr(role_raw, 'value'):
                        role = role_raw.value
                    
                    if role in agent_statuses:
                        agent_statuses[role]["status"] = "thinking"
                        agent_status_container.markdown(render_agent_status_cards(), unsafe_allow_html=True)
                    role_display = role.replace("_", " ").title()
                    update_log(f"🧠 {role_display} is deliberating")
                
                elif update.stage == ProgressStage.AGENT_COMPLETE:
                    # Get role and convert enum to string if needed
                    role_raw = update.detail.get("role", "")
                    role = str(role_raw).lower() if role_raw else ""
                    # Handle enum .value if present
                    if hasattr(role_raw, 'value'):
                        role = role_raw.value
                    
                    confidence = update.detail.get("confidence", 0)
                    round_num = update.detail.get("round_number", round_state["current"])
                    content = update.detail.get("content", "")
                    
                    if role in agent_statuses:
                        agent_statuses[role]["status"] = "done"
                        agent_statuses[role]["confidence"] = confidence
                        agent_status_container.markdown(render_agent_status_cards(), unsafe_allow_html=True)
                    
                    # Add to live dialogue if content is available
                    if content:
                        add_dialogue_entry(role, content, round_num)
                    
                    changed = " (position changed)" if update.detail.get("changed") else ""
                    role_display = role.replace("_", " ").title()
                    update_log(f"✓ {role_display} complete: {confidence:.0%}{changed}")
                
                elif update.stage == ProgressStage.ROUND_START:
                    round_num = update.detail.get("round_number", 1)
                    total = update.detail.get("total_rounds", 1)
                    
                    # Update round state and header
                    round_state["current"] = round_num
                    round_state["total"] = total
                    round_state["phase"] = "Deliberation"
                    header_container.markdown(render_header(), unsafe_allow_html=True)
                    
                    update_log(f"▸ Round {round_num}/{total} starting")
                    # Reset agent statuses for new round (except first)
                    if round_num > 1:
                        for role in agent_statuses:
                            agent_statuses[role]["status"] = "pending"
                            agent_statuses[role]["confidence"] = None
                        agent_status_container.markdown(render_agent_status_cards(), unsafe_allow_html=True)
                
                elif update.stage == ProgressStage.ROUND_COMPLETE:
                    round_num = update.detail.get("round_number", 1)
                    update_log(f"✓ Round {round_num} complete")
                
                elif update.stage == ProgressStage.GROUNDING:
                    # Update phase indicator
                    round_state["phase"] = "Verifying Citations"
                    header_container.markdown(render_header(), unsafe_allow_html=True)
                    
                    verified = update.detail.get("verified", 0)
                    failed = update.detail.get("failed", 0)
                    if verified or failed:
                        update_log(f"🔬 Citations verified: {verified} ✅, {failed} ❌")
                    else:
                        update_log("🔬 Verifying citations against PubMed...")
                
                elif update.stage == ProgressStage.ARBITRATION:
                    # Update phase indicator
                    round_state["phase"] = "Synthesizing"
                    header_container.markdown(render_header(), unsafe_allow_html=True)
                    
                    model = update.detail.get("model", "")
                    confidence = update.detail.get("confidence")
                    if confidence:
                        update_log(f"⚖️ Arbitrator synthesis complete: {confidence:.0%} confidence")
                    else:
                        update_log(f"⚖️ Arbitrator ({model}) synthesizing discussion...")
                
                elif update.stage == ProgressStage.FRAGILITY_START:
                    # Update phase indicator
                    round_state["phase"] = "Stress Testing"
                    header_container.markdown(render_header(), unsafe_allow_html=True)
                    
                    num_tests = update.detail.get("num_tests", 0)
                    update_log(f"🔥 Starting fragility testing ({num_tests} perturbations)...")
                
                elif update.stage == ProgressStage.FRAGILITY_TEST:
                    test_num = update.detail.get("test_number", 1)
                    total_tests = update.detail.get("total_tests", 1)
                    outcome = update.detail.get("outcome", "")
                    perturbation = update.detail.get("perturbation", "")[:40]
                    if outcome:
                        emoji = {"SURVIVES": "✅", "MODIFIES": "⚠️", "COLLAPSES": "❌"}.get(outcome, "❓")
                        update_log(f"🔥 Test {test_num}/{total_tests}: {emoji} {outcome} - {perturbation}...")
                    else:
                        update_log(f"🔥 Testing ({test_num}/{total_tests}): {perturbation}...")
                
                elif update.stage == ProgressStage.COMPLETE:
                    # Update phase indicator
                    round_state["phase"] = "Complete"
                    header_container.markdown(render_header(), unsafe_allow_html=True)
                    
                    duration = update.detail.get("duration_ms", 0)
                    tokens = update.detail.get("total_tokens", 0)
                    update_log(f"🎉 **Conference complete!** ({duration/1000:.1f}s, {tokens:,} tokens)")
            
            update_log("🚀 Conference started")
        
        try:
            # Run conference with progress callback
            result = asyncio.run(run_conference_async(
                query, 
                config,
                enable_grounding=config_options["enable_grounding"],
                enable_fragility=config_options["enable_fragility"],
                fragility_tests=config_options["fragility_tests"],
                progress_callback=progress_callback,
            ))
            
            progress_bar.progress(100)
            status_text.markdown("**✅ Conference complete!**")
            
            # Clear progress display after short delay
            import time
            time.sleep(1)
            progress_container.empty()
            
            # Results display
            st.markdown("---")
            
            # Synthesis first (most important)
            render_synthesis(result.synthesis)
            
            st.markdown("---")
            
            # Dissent
            render_dissent(result.dissent)
            
            st.markdown("---")
            
            # Grounding results
            if config_options["enable_grounding"]:
                render_grounding(result.grounding_report)
                st.markdown("---")
            
            # Fragility testing results
            if config_options["enable_fragility"]:
                render_fragility(result.fragility_report)
                st.markdown("---")
            
            # Detailed rounds (collapsed by default)
            st.markdown(
                '<div style="margin-top: 2rem;">'
                '<h3 style="color: var(--text-primary); font-weight: 600; margin-bottom: 1rem;">📜 Deliberation Details</h3>'
                '</div>',
                unsafe_allow_html=True
            )
            
            for round_result in result.rounds:
                with st.expander(f"Round {round_result.round_number}", expanded=False):
                    for agent_id, response in round_result.agent_responses.items():
                        role = response.role
                        emoji = get_role_emoji(role)
                        color = get_role_color(role)
                        conf_pct = response.confidence * 100
                        
                        changed_badge = ""
                        if response.changed_from_previous:
                            changed_badge = '<span style="background: var(--accent-info-dim); color: var(--accent-info); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 0.5rem;">Position Changed</span>'
                        
                        st.markdown(
                            f'<div class="agent-card {role}" style="margin-bottom: 1rem;">'
                            f'<div class="agent-header">'
                            f'<span class="agent-name {role}">{emoji} {role.replace("_", " ").title()}</span>'
                            f'<span class="agent-model">{response.model.split("/")[-1]}</span>'
                            f'<span style="margin-left: auto; font-size: 0.85rem; color: var(--text-muted);">{conf_pct:.0f}%</span>'
                            f'{changed_badge}'
                            f'</div></div>',
                            unsafe_allow_html=True
                        )
                        st.markdown(response.content)
                        st.markdown("---")
            
            st.markdown("---")
            
            # Metrics
            render_metrics(result)
            
            # Gatekeeper evaluation (Experience Library eligibility)
            if config_options["enable_learning"]:
                st.markdown("---")
                gatekeeper = Gatekeeper()
                gk_output = gatekeeper.evaluate(result)
                render_gatekeeper(gk_output, result)
                
                # Handle extraction request
                if st.session_state.get("extract_requested") and gk_output.eligible:
                    st.session_state["extract_requested"] = False
                    with st.spinner("Extracting heuristic..."):
                        client = LLMClient()
                        surgeon = Surgeon(client)
                        extraction = asyncio.run(surgeon.extract(result))
                        
                        render_extraction_result(
                            extraction.extraction_successful,
                            extraction.artifact,
                            extraction.failure_reason,
                        )
                        
                        # Save to library if successful
                        if extraction.extraction_successful and extraction.artifact:
                            library = get_experience_library()
                            library.add(extraction.artifact)
                            st.success("✅ Heuristic saved to Experience Library!")
            
            # Export options
            st.markdown("---")
            st.markdown("### 📥 Export")
            
            export_cols = st.columns(2)
            with export_cols[0]:
                # Export as JSON
                import json
                json_export = result.model_dump_json(indent=2)
                st.download_button(
                    "📄 Download JSON",
                    json_export,
                    file_name=f"conference_{result.conference_id}.json",
                    mime="application/json",
                )
            
            with export_cols[1]:
                # Copy synthesis
                st.code(result.synthesis.final_consensus, language=None)
            
            # Store config for optimizer
            st.session_state["last_config"] = config
            
            # Feedback form
            st.markdown("---")
            render_feedback_form(result.conference_id, result.dissent.preserved)
            
        except Exception as e:
            st.error(f"❌ Error running conference: {str(e)}")
            st.exception(e)
    
    elif run_button and not query:
        st.warning("Please enter a clinical question to start the conference.")


if __name__ == "__main__":
    main()

