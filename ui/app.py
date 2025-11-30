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

# Page configuration
st.set_page_config(
    page_title="AI Case Conference",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling (dark mode compatible)
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #58a6ff;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #8b949e;
        margin-bottom: 2rem;
    }
    .agent-card {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .advocate-header { color: #4CAF50; }
    .skeptic-header { color: #F44336; }
    .empiricist-header { color: #2196F3; }
    .synthesis-box {
        background-color: rgba(88, 166, 255, 0.15);
        border-left: 4px solid #58a6ff;
        padding: 1.5rem;
        border-radius: 0 10px 10px 0;
        color: inherit;
    }
    .synthesis-box h3 {
        color: #58a6ff;
        margin-top: 0;
    }
    .synthesis-box p {
        color: inherit;
    }
    .dissent-box {
        background-color: rgba(255, 193, 7, 0.15);
        border-left: 4px solid #ffc107;
        padding: 1.5rem;
        border-radius: 0 10px 10px 0;
        color: inherit;
    }
    .dissent-box h4 {
        color: #ffc107;
        margin-top: 0;
    }
    .dissent-box p {
        color: inherit;
    }
    .metric-card {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
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
    """Render the configuration sidebar."""
    st.sidebar.markdown("## ⚙️ Configuration")
    
    # Model selection
    st.sidebar.markdown("### Agent Models")
    st.sidebar.caption("🧠 = Thinking/Reasoning Model (uses more tokens)")
    
    advocate_model = st.sidebar.selectbox(
        "Advocate Model",
        options=list(AVAILABLE_MODELS.keys()),
        index=1,  # GPT-5.1
        help="Model for the Advocate agent who builds the case for the best approach",
    )
    
    skeptic_model = st.sidebar.selectbox(
        "Skeptic Model",
        options=list(AVAILABLE_MODELS.keys()),
        index=2,  # DeepSeek R1 - excellent value reasoning
        help="Model for the Skeptic agent who challenges the consensus",
    )
    
    empiricist_model = st.sidebar.selectbox(
        "Empiricist Model",
        options=list(AVAILABLE_MODELS.keys()),
        index=3,  # Gemini 3 Pro
        help="Model for the Empiricist agent who grounds in evidence",
    )
    
    arbitrator_model = st.sidebar.selectbox(
        "Arbitrator Model",
        options=list(AVAILABLE_MODELS.keys()),
        index=0,  # Claude Opus 4.5 - best for synthesis
        help="Model for the Arbitrator who synthesizes the discussion",
    )
    
    # Conference settings
    st.sidebar.markdown("### Conference Settings")
    
    num_rounds = st.sidebar.slider(
        "Deliberation Rounds",
        min_value=1,
        max_value=5,
        value=2,
        help="Number of rounds of discussion before synthesis",
    )
    
    # Grounding settings
    st.sidebar.markdown("### Citation Verification")
    
    enable_grounding = st.sidebar.checkbox(
        "Enable Grounding",
        value=True,
        help="Verify citations against PubMed (may add ~10s per round)",
    )
    
    # Fragility testing settings
    st.sidebar.markdown("### Fragility Testing")
    
    enable_fragility = st.sidebar.checkbox(
        "Enable Fragility Testing",
        value=True,
        help="Stress-test the recommendation against various clinical scenarios",
    )
    
    fragility_tests = st.sidebar.slider(
        "Number of Tests",
        min_value=1,
        max_value=6,
        value=3,
        help="Number of perturbations to test against",
        disabled=not enable_fragility,
    )
    
    # Experience Library settings
    st.sidebar.markdown("### Experience Library")
    
    enable_learning = st.sidebar.checkbox(
        "Enable Learning",
        value=True,
        help="Evaluate conference for Experience Library extraction",
    )
    
    return {
        "advocate_model": AVAILABLE_MODELS[advocate_model],
        "skeptic_model": AVAILABLE_MODELS[skeptic_model],
        "empiricist_model": AVAILABLE_MODELS[empiricist_model],
        "arbitrator_model": AVAILABLE_MODELS[arbitrator_model],
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
    """Render the final synthesis."""
    st.markdown("## 📋 Final Synthesis")
    
    st.markdown(f"""
    <div class="synthesis-box">
        <h3>Recommendation</h3>
        <p>{synthesis.final_consensus}</p>
        <p><strong>Confidence:</strong> {synthesis.confidence:.0%}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if synthesis.key_points:
        st.markdown("### Key Points of Agreement")
        for point in synthesis.key_points:
            st.markdown(f"- {point}")
    
    if synthesis.caveats:
        st.markdown("### ⚠️ Important Caveats")
        for caveat in synthesis.caveats:
            st.warning(caveat)


def render_dissent(dissent):
    """Render preserved dissent."""
    if not dissent.preserved:
        st.success("✅ All agents reached consensus - no significant dissent.")
        return
    
    st.markdown("## ⚖️ Preserved Dissent")
    
    st.markdown(f"""
    <div class="dissent-box">
        <h4>{get_role_emoji(dissent.dissenting_role or '')} Dissenting Agent: {dissent.dissenting_agent}</h4>
        <p><strong>Summary:</strong> {dissent.summary}</p>
        <p><strong>Reasoning:</strong> {dissent.reasoning}</p>
        <p><strong>Strength:</strong> {dissent.strength}</p>
    </div>
    """, unsafe_allow_html=True)


def render_grounding(grounding_report: GroundingReport):
    """Render grounding/citation verification results."""
    st.markdown("## 🔬 Citation Verification")
    
    if grounding_report is None:
        st.info("Citation verification was not enabled for this conference.")
        return
    
    if grounding_report.total_citations == 0:
        st.info("No citations were found in agent responses.")
        return
    
    # Summary metrics
    cols = st.columns(3)
    
    with cols[0]:
        st.metric(
            "Citations Found",
            grounding_report.total_citations,
        )
    
    with cols[1]:
        st.metric(
            "Verified",
            len(grounding_report.citations_verified),
        )
    
    with cols[2]:
        hallucination_pct = grounding_report.hallucination_rate * 100
        st.metric(
            "Hallucination Rate",
            f"{hallucination_pct:.0f}%",
            delta=None if hallucination_pct == 0 else f"-{hallucination_pct:.0f}%",
            delta_color="inverse" if hallucination_pct > 0 else "off",
        )
    
    # Warning for high hallucination rate
    if grounding_report.hallucination_rate > 0.2:
        st.error(
            f"⚠️ High hallucination rate detected! {len(grounding_report.citations_failed)} of "
            f"{grounding_report.total_citations} citations could not be verified."
        )
    elif grounding_report.has_failures:
        st.warning(
            f"⚠️ Some citations could not be verified: {len(grounding_report.citations_failed)} failed."
        )
    else:
        st.success("✅ All citations were verified successfully!")
    
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
    """Render fragility testing results."""
    st.markdown("## 🔥 Fragility Testing")
    
    if fragility_report is None:
        st.info("Fragility testing was not enabled for this conference.")
        return
    
    if fragility_report.perturbations_tested == 0:
        st.info("No fragility tests were run.")
        return
    
    # Summary metrics
    cols = st.columns(4)
    
    with cols[0]:
        st.metric(
            "Tests Run",
            fragility_report.perturbations_tested,
        )
    
    with cols[1]:
        st.metric(
            "Survived",
            len(fragility_report.survived),
        )
    
    with cols[2]:
        st.metric(
            "Modified",
            len(fragility_report.modified),
        )
    
    with cols[3]:
        survival_pct = fragility_report.survival_rate * 100
        st.metric(
            "Survival Rate",
            f"{survival_pct:.0f}%",
        )
    
    # Fragility level indicator
    level = fragility_report.fragility_level
    if level == "LOW":
        st.success(f"✅ **Fragility: {level}** - Recommendation is robust across tested scenarios")
    elif level == "MODERATE":
        st.warning(f"⚠️ **Fragility: {level}** - Recommendation needs consideration in some scenarios")
    else:
        st.error(f"🚨 **Fragility: {level}** - Recommendation may not apply in many scenarios")
    
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
    """Render conference metrics."""
    st.markdown("## 📊 Conference Metrics")
    
    cols = st.columns(4)
    
    with cols[0]:
        st.metric(
            "Total Tokens",
            f"{result.token_usage.total_tokens:,}",
        )
    
    with cols[1]:
        st.metric(
            "Estimated Cost",
            f"${result.token_usage.estimated_cost_usd:.4f}",
        )
    
    with cols[2]:
        st.metric(
            "Duration",
            f"{result.duration_ms / 1000:.1f}s",
        )
    
    with cols[3]:
        st.metric(
            "Rounds",
            len(result.rounds),
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
    """Render the immediate feedback form."""
    st.markdown("## 📝 Quick Feedback")
    st.markdown("*Your feedback helps improve future consultations.*")
    
    with st.form(key=f"feedback_form_{conference_id}"):
        col1, col2 = st.columns(2)
        
        with col1:
            useful = st.radio(
                "Was this consultation useful?",
                options=["", "yes", "partially", "no"],
                format_func=lambda x: {"": "Select...", "yes": "✅ Yes", "partially": "🔶 Partially", "no": "❌ No"}.get(x, x),
                horizontal=True,
            )
        
        with col2:
            will_act = st.radio(
                "Will you act on this recommendation?",
                options=["", "yes", "modified", "no"],
                format_func=lambda x: {"": "Select...", "yes": "✅ Yes", "modified": "✏️ Modified", "no": "❌ No"}.get(x, x),
                horizontal=True,
            )
        
        dissent_useful = None
        if has_dissent:
            dissent_useful = st.checkbox(
                "The dissent flagged something important",
                value=False,
            )
        
        submitted = st.form_submit_button("Submit Feedback", use_container_width=True)
        
        if submitted:
            collector = get_feedback_collector()
            collector.record_immediate(
                conference_id,
                useful=useful if useful else None,
                will_act=will_act if will_act else None,
                dissent_useful=dissent_useful,
            )
            
            # Also update optimizer if we have outcome
            outcome = collector.get_outcome(conference_id)
            if outcome is not None and "last_config" in st.session_state:
                optimizer = get_optimizer()
                query_class = QueryClassification(query_type="general")
                optimizer.update(query_class, st.session_state["last_config"], outcome)
            
            st.success("✅ Thank you for your feedback!")
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
    # Header
    st.markdown('<p class="main-header">🏥 AI Case Conference</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Multi-agent deliberation for complex clinical decisions</p>',
        unsafe_allow_html=True,
    )
    
    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY"):
        st.error(
            "⚠️ OpenRouter API key not found. Please set the `OPENROUTER_API_KEY` "
            "environment variable or create a `.env` file."
        )
        st.stop()
    
    # Sidebar configuration
    config_options = render_sidebar()
    
    # Show library stats if learning is enabled
    if config_options.get("enable_learning", True):
        library = get_experience_library()
        render_library_stats(library)
        render_optimizer_insights()
        render_shadow_summary()
    
    # Main input area
    st.markdown("### 💬 Enter Your Clinical Question")
    
    query = st.text_area(
        "Clinical Question",
        placeholder="Example: 62-year-old male with cold-type CRPS of the right hand, "
                    "failed gabapentin and physical therapy. What treatment approach "
                    "would you recommend?",
        height=150,
        label_visibility="collapsed",
    )
    
    # Run button
    run_button = st.button("🚀 Start Conference", type="primary", use_container_width=True)
    
    if run_button and query:
        # Create configuration
        config = create_default_config(
            advocate_model=config_options["advocate_model"],
            skeptic_model=config_options["skeptic_model"],
            empiricist_model=config_options["empiricist_model"],
            arbitrator_model=config_options["arbitrator_model"],
            num_rounds=config_options["num_rounds"],
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
        
        # Show classification
        render_classification(classification)
        
        # Show injection info if any heuristics matched
        if injection_result:
            st.markdown("---")
            render_injection_info(injection_result)
        
        # Progress display
        progress_container = st.container()
        
        with progress_container:
            st.markdown("---")
            st.markdown("### 🔄 Conference in Progress...")
            
            # Main progress bar
            progress_bar = st.progress(0)
            
            # Status message
            status_text = st.empty()
            
            # Agent status table (will be updated dynamically)
            st.markdown("**Agent Status:**")
            agent_status_container = st.empty()
            
            # Initialize agent status tracking
            agent_statuses = {
                "advocate": {"status": "⏳ Pending", "model": config_options['advocate_model'].split('/')[-1], "confidence": None},
                "skeptic": {"status": "⏳ Pending", "model": config_options['skeptic_model'].split('/')[-1], "confidence": None},
                "empiricist": {"status": "⏳ Pending", "model": config_options['empiricist_model'].split('/')[-1], "confidence": None},
            }
            
            # Render initial agent status
            def render_agent_status_table():
                status_md = "| Agent | Model | Status | Confidence |\n|-------|-------|--------|------------|\n"
                for role, info in agent_statuses.items():
                    emoji = {"advocate": "🟢", "skeptic": "🔴", "empiricist": "🔵"}.get(role, "⚪")
                    conf = f"{info['confidence']:.0%}" if info['confidence'] else "-"
                    status_md += f"| {emoji} **{role.title()}** | `{info['model']}` | {info['status']} | {conf} |\n"
                return status_md
            
            agent_status_container.markdown(render_agent_status_table())
            
            # Live log expander
            log_container = st.expander("📋 Live Activity Log", expanded=True)
            log_messages = []
            log_display = log_container.empty()
            
            def update_log(message: str):
                """Add a message to the live log."""
                import datetime
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                log_messages.append(f"`{timestamp}` {message}")
                # Keep only last 15 messages
                if len(log_messages) > 15:
                    log_messages.pop(0)
                log_display.markdown("\n\n".join(log_messages))
            
            # Create progress callback
            def progress_callback(update: ProgressUpdate):
                """Handle progress updates from the conference engine."""
                # Update progress bar
                progress_bar.progress(min(update.percent, 100))
                
                # Update status text
                status_text.markdown(f"**{update.message}**")
                
                # Handle stage-specific updates
                if update.stage == ProgressStage.AGENT_THINKING:
                    role = update.detail.get("role", "")
                    if role in agent_statuses:
                        agent_statuses[role]["status"] = "🔄 Thinking..."
                        agent_status_container.markdown(render_agent_status_table())
                    update_log(f"🧠 {update.detail.get('role', '').title()} is deliberating ({update.detail.get('model', '')})")
                
                elif update.stage == ProgressStage.AGENT_COMPLETE:
                    role = update.detail.get("role", "")
                    confidence = update.detail.get("confidence", 0)
                    if role in agent_statuses:
                        agent_statuses[role]["status"] = "✅ Done"
                        agent_statuses[role]["confidence"] = confidence
                        agent_status_container.markdown(render_agent_status_table())
                    changed = "📝 (position changed)" if update.detail.get("changed") else ""
                    update_log(f"✅ {role.title()} complete: {confidence:.0%} confidence {changed}")
                
                elif update.stage == ProgressStage.ROUND_START:
                    round_num = update.detail.get("round_number", 1)
                    total = update.detail.get("total_rounds", 1)
                    update_log(f"📍 **Round {round_num} of {total} starting**")
                    # Reset agent statuses for new round (except first)
                    if round_num > 1:
                        for role in agent_statuses:
                            agent_statuses[role]["status"] = "⏳ Pending"
                            agent_statuses[role]["confidence"] = None
                        agent_status_container.markdown(render_agent_status_table())
                
                elif update.stage == ProgressStage.ROUND_COMPLETE:
                    round_num = update.detail.get("round_number", 1)
                    update_log(f"🏁 Round {round_num} complete")
                
                elif update.stage == ProgressStage.GROUNDING:
                    verified = update.detail.get("verified", 0)
                    failed = update.detail.get("failed", 0)
                    if verified or failed:
                        update_log(f"🔬 Citations verified: {verified} ✅, {failed} ❌")
                    else:
                        update_log("🔬 Verifying citations against PubMed...")
                
                elif update.stage == ProgressStage.ARBITRATION:
                    model = update.detail.get("model", "")
                    confidence = update.detail.get("confidence")
                    if confidence:
                        update_log(f"⚖️ Arbitrator synthesis complete: {confidence:.0%} confidence")
                    else:
                        update_log(f"⚖️ Arbitrator ({model}) synthesizing discussion...")
                
                elif update.stage == ProgressStage.FRAGILITY_START:
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
            st.markdown("## 📜 Deliberation Details")
            
            for round_result in result.rounds:
                with st.expander(f"Round {round_result.round_number}", expanded=False):
                    for agent_id, response in round_result.agent_responses.items():
                        role = response.role
                        emoji = get_role_emoji(role)
                        
                        st.markdown(f"#### {emoji} {role.title()}")
                        st.markdown(f"*Model: `{response.model}` | Confidence: {response.confidence:.0%}*")
                        if response.changed_from_previous:
                            st.info("📝 Position changed from previous round")
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

