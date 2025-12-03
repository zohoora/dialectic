"""
Result rendering components for the AI Case Conference UI.

Renders synthesis, dissent, grounding, fragility, and metrics displays.
"""

import streamlit as st

from src.models.conference import ConferenceResult
from src.models.fragility import FragilityOutcome, FragilityReport
from src.models.grounding import GroundingReport
from ui.config import get_role_color, get_role_emoji


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

