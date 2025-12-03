"""
Feedback and gatekeeper components for the AI Case Conference UI.

Renders feedback forms, gatekeeper evaluation, and extraction results.
"""

import streamlit as st

from src.models.conference import ConferenceResult
from src.models.feedback import QueryClassification
from src.models.gatekeeper import GatekeeperOutput
from ui.services.state import get_feedback_collector, get_optimizer


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
            if collector is not None:
                collector.record_immediate(
                    conference_id,
                    useful=useful_map.get(useful),
                    will_act=will_act,
                    dissent_useful=dissent_useful,
                )
                
                # Also update optimizer if we have outcome
                outcome = collector.get_outcome(conference_id)
                last_run_id = st.session_state.get("last_config_run_id")
                config_key = f"last_config_{last_run_id}" if last_run_id else None
                if outcome is not None and config_key and config_key in st.session_state:
                    optimizer = get_optimizer()
                    if optimizer is not None:
                        query_class = QueryClassification(query_type="general")
                        optimizer.update(query_class, st.session_state[config_key], outcome)
            
            st.markdown(
                '<div style="background: var(--accent-primary-dim); border: 1px solid var(--accent-primary); border-radius: 8px; padding: 1rem; text-align: center; margin-top: 0.5rem;">'
                '<span style="color: var(--accent-primary);">✓ Thank you for your feedback!</span>'
                '</div>',
                unsafe_allow_html=True
            )
            return True
    
    return False

