"""
Learning and experience library components for the AI Case Conference UI.

Renders library stats, optimizer insights, query classification,
heuristic injection info, and shadow mode summary.
"""

import streamlit as st

from src.learning.classifier import ClassifiedQuery
from src.learning.library import ExperienceLibrary
from src.models.experience import InjectionResult
from ui.services.state import get_optimizer, get_shadow_runner


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


def render_optimizer_insights():
    """Render optimizer insights in sidebar."""
    optimizer = get_optimizer()
    if optimizer is None:
        return  # Optimizer failed to initialize
    
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


def render_shadow_summary(api_key: str):
    """Render shadow mode summary in sidebar."""
    runner = get_shadow_runner(api_key)
    if runner is None:
        # Shadow runner failed to initialize, skip display
        return
    
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

