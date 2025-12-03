"""
Sidebar component for the AI Case Conference UI.

Renders the configuration sidebar with agent selection, topology, and quality settings.
"""

import streamlit as st

from ui.config import AVAILABLE_MODELS

# Default librarian model
DEFAULT_LIBRARIAN_MODEL = "google/gemini-2.0-flash-001"


def render_sidebar() -> dict:
    """Render the configuration sidebar with collapsible sections.
    
    Returns:
        Dict with configuration options including:
        - active_agents: Dict mapping role to model ID
        - arbitrator_model: Model ID for arbitrator
        - topology: Conference topology type
        - num_rounds: Number of deliberation rounds
        - enable_grounding: Whether to verify citations
        - enable_fragility: Whether to run fragility testing
        - fragility_tests: Number of perturbation tests
        - fragility_model: Model for generating perturbations
        - enable_learning: Whether to use experience library
    """
    
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
                min_value=1, max_value=10,
                value=preset_config["frag_tests"],
                help="Number of perturbation scenarios to test",
            )
            fragility_model = st.selectbox(
                "Perturbation Generator",
                options=list(AVAILABLE_MODELS.keys()),
                index=0,
                help="Model for generating query-specific perturbations",
            )
        else:
            fragility_tests = 3
            fragility_model = None
        
        enable_learning = st.toggle(
            "Experience Library",
            value=True,
            help="Extract learnings for future use",
        )
    
    # Librarian Settings
    with st.sidebar.expander("📚 **Librarian**", expanded=False):
        st.caption("Document analysis agent")
        
        # Librarian model selection - multimodal models for document analysis
        librarian_models = {
            "🧠 Gemini 3 Pro": "google/gemini-3-pro-preview",
            "🧠 Claude Opus 4.5": "anthropic/claude-opus-4.5",
        }
        
        librarian_model = st.selectbox(
            "Analysis Model",
            options=list(librarian_models.keys()),
            index=0,
            help="Multimodal model for document analysis (must support PDFs/images)",
        )
        
        max_queries_per_turn = st.slider(
            "Max Queries per Agent/Turn",
            min_value=1,
            max_value=10,
            value=3,
            help="Maximum document queries each agent can make per round",
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
        "fragility_model": AVAILABLE_MODELS[fragility_model] if fragility_model else None,
        "enable_learning": enable_learning,
        # Librarian settings
        "librarian_model": librarian_models[librarian_model],
        "librarian_max_queries": max_queries_per_turn,
    }

