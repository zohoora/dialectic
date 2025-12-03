"""
Streamlit UI for AI Case Conference System.

This provides a web interface for running case conferences with
multiple AI agents deliberating on clinical questions.
"""

import time
import uuid
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from dotenv import load_dotenv

from src.conference.engine import create_default_config, ProgressStage, ProgressUpdate
from src.learning.classifier import QueryClassifier
from src.learning.gatekeeper import Gatekeeper
from src.learning.injector import HeuristicInjector
from src.learning.surgeon import Surgeon
from src.llm.client import LLMClient
from src.models.librarian import LibrarianConfig

# UI module imports
from ui.styles import STYLES
from ui.config import EXAMPLE_QUERIES, get_role_color, get_role_emoji
from ui.utils import run_async, get_api_key
from ui.services.state import get_experience_library, get_shadow_runner
from ui.services.conference import run_conference_async
from ui.components.sidebar import render_sidebar
from ui.components.results import (
    render_synthesis,
    render_dissent,
    render_grounding,
    render_fragility,
    render_metrics,
)
from ui.components.feedback import (
    render_gatekeeper,
    render_extraction_result,
    render_feedback_form,
)
from ui.components.files import (
    render_file_upload,
    render_librarian_summary,
)
from ui.components.learning import (
    render_library_stats,
    render_optimizer_insights,
    render_injection_info,
    render_shadow_summary,
)
from ui.components.progress import (
    ROLE_COLORS,
    ROLE_EMOJIS,
    render_agent_status_cards,
    render_progress_header,
    render_dialogue_entries,
    create_log_message,
    get_topology_info,
)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Case Conference",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply styles
st.markdown(STYLES, unsafe_allow_html=True)


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
    
    # Sidebar configuration
    config_options = render_sidebar()
    
    # Show library stats if learning is enabled
    if config_options.get("enable_learning", True):
        library = get_experience_library()
        if library is not None:
            render_library_stats(library)
        render_optimizer_insights()
        render_shadow_summary(api_key)
    
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
    
    # File upload for Librarian
    librarian_files = render_file_upload()
    
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
        _run_conference(query, config_options, api_key, librarian_files)
    elif run_button and not query:
        st.warning("Please enter a clinical question to start the conference.")


def _run_conference(query: str, config_options: dict, api_key: str, librarian_files: list = None):
    """Run the conference with the given query and configuration."""
    # Generate unique run ID for this conference
    run_id = str(uuid.uuid4())[:8]
    st.session_state["current_run_id"] = run_id
    
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
    
    # Create librarian config if files provided
    librarian_config = None
    if librarian_files:
        librarian_config = LibrarianConfig(
            model=config_options.get("librarian_model", "google/gemini-3-pro-preview"),
            max_queries_per_turn=config_options.get("librarian_max_queries", 3),
        )
    
    # Classify the query
    classifier = QueryClassifier()
    classification = classifier.classify(query)
    
    # Get heuristic injection if learning is enabled
    injection_result = None
    if config_options.get("enable_learning", True):
        library = get_experience_library()
        if library is not None:
            injector = HeuristicInjector(library)
            injection_result = injector.get_injection_for_query(classification)
    
    # Show injection info if any heuristics matched
    if injection_result:
        st.markdown("---")
        render_injection_info(injection_result)
    
    # Progress display with enhanced styling
    progress_container = st.container()
    
    # Track round state for UI
    round_state = {"current": 1, "total": config_options["num_rounds"], "phase": "deliberation"}
    
    # Get topology display info
    topology_name, topology_desc = get_topology_info(config_options["topology"])
    
    with progress_container:
        # Header with round indicator
        header_container = st.empty()
        
        def update_header():
            header_container.markdown(
                render_progress_header(round_state, topology_name, topology_desc),
                unsafe_allow_html=True
            )
        
        update_header()
        
        # Main progress bar
        progress_bar = st.progress(0)
        
        # Status message
        status_text = st.empty()
        
        # Agent status as styled cards
        agent_status_container = st.empty()
        
        # Initialize agent status tracking
        agent_statuses = {}
        for role, model in config_options['active_agents'].items():
            agent_statuses[role] = {
                "status": "pending", 
                "model": model.split('/')[-1], 
                "confidence": None
            }
        
        agent_status_container.markdown(render_agent_status_cards(agent_statuses), unsafe_allow_html=True)
        
        # Live dialogue/transcript view
        dialogue_key = f"dialogue_entries_{run_id}"
        st.session_state[dialogue_key] = []
        dialogue_entries = st.session_state[dialogue_key]
        
        dialogue_container = st.expander("🎙️ Live Dialogue (listen in)", expanded=False)
        with dialogue_container:
            dialogue_display = st.empty()
        
        def add_dialogue_entry(role: str, content: str, round_num: int):
            """Add an agent response to the live dialogue."""
            color = ROLE_COLORS.get(role, "#64748b")
            emoji = ROLE_EMOJIS.get(role, "⚪")
            display_name = role.replace("_", " ").title()
            dialogue_entries.append({
                "role": role,
                "display_name": display_name,
                "content": content,
                "round": round_num,
                "color": color,
                "emoji": emoji,
            })
            dialogue_display.markdown(render_dialogue_entries(dialogue_entries), unsafe_allow_html=True)
        
        dialogue_display.markdown(render_dialogue_entries(dialogue_entries), unsafe_allow_html=True)
        
        # Activity timeline (more compact)
        log_container = st.expander("📋 Activity Log", expanded=False)
        log_messages = []
        log_display = log_container.empty()
        
        def update_log(message: str):
            """Add a message to the live log."""
            log_messages.append(create_log_message(message))
            if len(log_messages) > 15:
                log_messages.pop(0)
            log_display.markdown("\n".join(log_messages), unsafe_allow_html=True)
        
        # Create progress callback
        def progress_callback(update: ProgressUpdate):
            """Handle progress updates from the conference engine."""
            progress_bar.progress(min(update.percent, 100))
            
            status_text.markdown(
                f'<p style="color: var(--text-secondary); font-size: 0.95rem; margin: 0.5rem 0;">{update.message}</p>',
                unsafe_allow_html=True
            )
            
            if update.stage == ProgressStage.AGENT_THINKING:
                role_raw = update.detail.get("role", "")
                role = str(role_raw).lower() if role_raw else ""
                if hasattr(role_raw, 'value'):
                    role = role_raw.value
                
                if role in agent_statuses:
                    agent_statuses[role]["status"] = "thinking"
                    agent_status_container.markdown(render_agent_status_cards(agent_statuses), unsafe_allow_html=True)
                role_display = role.replace("_", " ").title()
                update_log(f"🧠 {role_display} is deliberating")
            
            elif update.stage == ProgressStage.AGENT_COMPLETE:
                role_raw = update.detail.get("role", "")
                role = str(role_raw).lower() if role_raw else ""
                if hasattr(role_raw, 'value'):
                    role = role_raw.value
                
                confidence = update.detail.get("confidence", 0)
                round_num = update.detail.get("round_number", round_state["current"])
                content = update.detail.get("content", "")
                
                if role in agent_statuses:
                    agent_statuses[role]["status"] = "done"
                    agent_statuses[role]["confidence"] = confidence
                    agent_status_container.markdown(render_agent_status_cards(agent_statuses), unsafe_allow_html=True)
                
                if content:
                    add_dialogue_entry(role, content, round_num)
                
                changed = " (position changed)" if update.detail.get("changed") else ""
                role_display = role.replace("_", " ").title()
                update_log(f"✓ {role_display} complete: {confidence:.0%}{changed}")
            
            elif update.stage == ProgressStage.ROUND_START:
                round_num = update.detail.get("round_number", 1)
                total = update.detail.get("total_rounds", 1)
                
                round_state["current"] = round_num
                round_state["total"] = total
                round_state["phase"] = "Deliberation"
                update_header()
                
                update_log(f"▸ Round {round_num}/{total} starting")
                if round_num > 1:
                    for role in agent_statuses:
                        agent_statuses[role]["status"] = "pending"
                        agent_statuses[role]["confidence"] = None
                    agent_status_container.markdown(render_agent_status_cards(agent_statuses), unsafe_allow_html=True)
            
            elif update.stage == ProgressStage.ROUND_COMPLETE:
                round_num = update.detail.get("round_number", 1)
                update_log(f"✓ Round {round_num} complete")
            
            elif update.stage == ProgressStage.GROUNDING:
                round_state["phase"] = "Verifying Citations"
                update_header()
                
                verified = update.detail.get("verified", 0)
                failed = update.detail.get("failed", 0)
                if verified or failed:
                    update_log(f"🔬 Citations verified: {verified} ✅, {failed} ❌")
                else:
                    update_log("🔬 Verifying citations against PubMed...")
            
            elif update.stage == ProgressStage.ARBITRATION:
                round_state["phase"] = "Synthesizing"
                update_header()
                
                model = update.detail.get("model", "")
                confidence = update.detail.get("confidence")
                if confidence:
                    update_log(f"⚖️ Arbitrator synthesis complete: {confidence:.0%} confidence")
                else:
                    update_log(f"⚖️ Arbitrator ({model}) synthesizing discussion...")
            
            elif update.stage == ProgressStage.FRAGILITY_START:
                round_state["phase"] = "Stress Testing"
                update_header()
                
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
            
            elif update.stage == ProgressStage.LIBRARIAN_ANALYSIS:
                round_state["phase"] = "Analyzing Documents"
                update_header()
                
                num_files = update.detail.get("num_files", 0)
                input_tokens = update.detail.get("input_tokens")
                if input_tokens:
                    update_log(f"📚 Document analysis complete ({input_tokens:,} tokens processed)")
                else:
                    update_log(f"📚 Librarian analyzing {num_files} document(s)...")
            
            elif update.stage == ProgressStage.COMPLETE:
                round_state["phase"] = "Complete"
                update_header()
                
                duration = update.detail.get("duration_ms", 0)
                tokens = update.detail.get("total_tokens", 0)
                update_log(f"🎉 **Conference complete!** ({duration/1000:.1f}s, {tokens:,} tokens)")
        
        update_log("🚀 Conference started")
        if librarian_files:
            update_log(f"📎 {len(librarian_files)} document(s) for Librarian analysis")
    
    try:
        # Run conference with progress callback
        result, librarian_summary = run_async(run_conference_async(
            query, 
            config,
            api_key=api_key,
            enable_grounding=config_options["enable_grounding"],
            enable_fragility=config_options["enable_fragility"],
            fragility_tests=config_options["fragility_tests"],
            fragility_model=config_options["fragility_model"],
            librarian_files=librarian_files or None,
            librarian_config=librarian_config,
            progress_callback=progress_callback,
        ))
        
        progress_bar.progress(100)
        status_text.markdown("**✅ Conference complete!**")
        
        # Clear progress display after short delay
        time.sleep(1)
        progress_container.empty()
        
        # Show librarian summary if present
        if librarian_summary:
            render_librarian_summary(librarian_summary)
        
        # Results display
        _render_results(result, config_options, api_key, run_id)
        
    except Exception as e:
        st.error(f"❌ Error running conference: {str(e)}")
        st.exception(e)


def _render_results(result, config_options: dict, api_key: str, run_id: str):
    """Render the conference results."""
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
                client = LLMClient(api_key=api_key)
                surgeon = Surgeon(client)
                extraction = run_async(surgeon.extract(result))
                
                render_extraction_result(
                    extraction.extraction_successful,
                    extraction.artifact,
                    extraction.failure_reason,
                )
                
                # Save to library if successful
                if extraction.extraction_successful and extraction.artifact:
                    library = get_experience_library()
                    if library is not None:
                        library.add(extraction.artifact)
                    st.success("✅ Heuristic saved to Experience Library!")
    
    # Export options
    st.markdown("---")
    st.markdown("### 📥 Export")
    
    export_cols = st.columns(2)
    with export_cols[0]:
        # Export as JSON
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
    
    # Store config for optimizer with run_id namespace
    config_key = f"last_config_{run_id}"
    st.session_state[config_key] = config_options
    st.session_state["last_config_run_id"] = run_id
    
    # Feedback form
    st.markdown("---")
    render_feedback_form(result.conference_id, result.dissent.preserved)


if __name__ == "__main__":
    main()
