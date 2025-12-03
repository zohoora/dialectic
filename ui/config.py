"""
Configuration constants for the AI Case Conference UI.

This module contains model configurations, role styling, and example queries.
"""

# Available models on OpenRouter (all thinking/reasoning models)
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

# Example queries for the UI
EXAMPLE_QUERIES = [
    ("CRPS", "62-year-old male with cold-type CRPS of the right hand, failed gabapentin and physical therapy. What treatment approach would you recommend?"),
    ("Drug interaction", "Patient on warfarin needs NSAID for acute gout flare. How should I manage anticoagulation and pain?"),
    ("Depression", "45-year-old with treatment-resistant depression, failed 3 SSRIs and SNRIs. What are the next steps?"),
]

# Role colors for agent styling
ROLE_COLORS = {
    "advocate": "#4CAF50",
    "skeptic": "#F44336",
    "empiricist": "#2196F3",
    "mechanist": "#9C27B0",
    "patient_voice": "#FF9800",
    "arbitrator": "#607D8B",
}

# Role emojis for agent display
ROLE_EMOJIS = {
    "advocate": "🟢",
    "skeptic": "🔴",
    "empiricist": "🔵",
    "mechanist": "🟣",
    "patient_voice": "🟠",
    "arbitrator": "⚖️",
}

# CSS colors for progress display (slightly different shade)
ROLE_COLORS_CSS = {
    "advocate": "#22c55e",
    "skeptic": "#f43f5e",
    "empiricist": "#0ea5e9",
    "mechanist": "#a855f7",
    "patient_voice": "#f97316",
}

# Topology configuration
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

TOPOLOGY_DISPLAY_NAMES = {
    "free_discussion": ("Free Discussion", "All agents deliberate openly"),
    "oxford_debate": ("Oxford Debate", "Structured proposition vs opposition"),
    "delphi_method": ("Delphi Method", "Anonymous iterative consensus"),
    "socratic_spiral": ("Socratic Spiral", "Question-driven exploration"),
    "red_team_blue_team": ("Red Team / Blue Team", "Adversarial challenge & defense"),
}

# Preset configurations
PRESET_CONFIGS = {
    "fast": {"rounds": 1, "grounding": False, "fragility": False, "frag_tests": 2},
    "balanced": {"rounds": 2, "grounding": True, "fragility": True, "frag_tests": 3},
    "deep": {"rounds": 3, "grounding": True, "fragility": True, "frag_tests": 5},
}


def get_role_color(role: str) -> str:
    """Get color for agent role."""
    return ROLE_COLORS.get(role, "#666666")


def get_role_emoji(role: str) -> str:
    """Get emoji for agent role."""
    return ROLE_EMOJIS.get(role, "⚪")

