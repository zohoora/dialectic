"""
Prompt loading and formatting utilities.

Handles loading role prompts from markdown files and formatting them
with variable substitution.
"""

import os
from pathlib import Path
from typing import Optional


# Base directory for prompts (relative to project root)
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def load_prompt(role: str, category: str = "agents") -> str:
    """
    Load a prompt template from a markdown file.
    
    Args:
        role: The role name (e.g., "advocate", "skeptic")
        category: The prompt category (e.g., "agents", "gatekeeper")
    
    Returns:
        The prompt template as a string
    
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    prompt_path = PROMPTS_DIR / category / f"{role}.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}. "
            f"Expected prompt for role '{role}' in category '{category}'."
        )
    
    return prompt_path.read_text()


def format_prompt(template: str, **kwargs) -> str:
    """
    Format a prompt template with variable substitution.
    
    Uses simple {variable} replacement syntax.
    
    Args:
        template: The prompt template string
        **kwargs: Variables to substitute
    
    Returns:
        The formatted prompt string
    """
    result = template
    for key, value in kwargs.items():
        placeholder = "{" + key + "}"
        result = result.replace(placeholder, str(value))
    return result


def build_agent_system_prompt(role: str, include_librarian: bool = False) -> str:
    """
    Build the complete system prompt for an agent.
    
    Args:
        role: The agent role (e.g., "advocate")
        include_librarian: Whether to include librarian query instructions
    
    Returns:
        The formatted system prompt
    """
    prompt = load_prompt(role, "agents")
    
    if include_librarian:
        try:
            librarian_instructions = load_prompt("query_instructions", "librarian")
            prompt = prompt + "\n\n" + librarian_instructions
        except FileNotFoundError:
            pass  # Librarian instructions not available
    
    return prompt


def build_round_one_user_prompt(query: str) -> str:
    """
    Build the user prompt for the first round.
    
    Args:
        query: The clinical question to discuss
    
    Returns:
        The formatted user prompt
    """
    return f"""## Clinical Question

{query}

---

Please provide your analysis of this case according to your assigned role. Follow the output format specified in your system prompt.
"""


def build_followup_round_prompt(
    query: str,
    previous_responses: dict[str, str],
    round_number: int,
) -> str:
    """
    Build the user prompt for follow-up rounds.
    
    Args:
        query: The original clinical question
        previous_responses: Dict mapping agent roles to their previous responses
        round_number: The current round number
    
    Returns:
        The formatted user prompt for critique/refinement
    """
    responses_text = ""
    for role, response in previous_responses.items():
        responses_text += f"\n### {role.title()}'s Position\n\n{response}\n"
    
    return f"""## Clinical Question

{query}

---

## Previous Round Discussion

The following positions were expressed in Round {round_number - 1}:

{responses_text}

---

## Your Task for Round {round_number}

Review the other participants' positions and:
1. Address any valid concerns raised about your position
2. Critique weaknesses in other positions if appropriate
3. Note if your position has changed based on the discussion
4. Refine your recommendation if needed

If you are changing your position, explicitly state "**Position Changed**" and explain why.

Follow the output format specified in your system prompt.
"""


def build_arbitrator_prompt(
    query: str,
    all_rounds: list[dict[str, str]],
) -> str:
    """
    Build the prompt for the arbitrator to synthesize the discussion.
    
    Args:
        query: The original clinical question
        all_rounds: List of dicts, each mapping agent roles to their responses for that round
    
    Returns:
        The formatted arbitrator prompt
    """
    rounds_text = ""
    for i, round_responses in enumerate(all_rounds, 1):
        rounds_text += f"\n## Round {i}\n"
        for role, response in round_responses.items():
            rounds_text += f"\n### {role.title()}\n\n{response}\n"
    
    return f"""## Clinical Question

{query}

---

## Conference Discussion

The following deliberation took place:

{rounds_text}

---

## Your Task

As the Arbitrator, synthesize this discussion into a final recommendation. Follow the output format specified in your system prompt.

Pay particular attention to:
- Points where all agents agree
- Valid concerns that were not fully addressed
- Any agent whose position did not converge with the others (this may indicate important dissent to preserve)
"""


def get_available_roles() -> list[str]:
    """
    Get list of available agent roles.
    
    Returns:
        List of role names with prompt files
    """
    agents_dir = PROMPTS_DIR / "agents"
    if not agents_dir.exists():
        return []
    
    roles = []
    for file in agents_dir.glob("*.md"):
        role = file.stem  # filename without extension
        if role != "arbitrator":  # Arbitrator is special
            roles.append(role)
    return roles

