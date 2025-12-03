"""
Progress display components for the AI Case Conference UI.

Handles live progress updates, agent status cards, and dialogue display.
"""

import datetime
import html
from typing import Callable

import streamlit as st

from src.conference.engine import ProgressStage, ProgressUpdate


# Role colors and emojis for agent display
ROLE_COLORS = {
    "advocate": "#22c55e",
    "skeptic": "#f43f5e",
    "empiricist": "#0ea5e9",
    "mechanist": "#a855f7",
    "patient_voice": "#f97316",
}

ROLE_EMOJIS = {
    "advocate": "🟢",
    "skeptic": "🔴",
    "empiricist": "🔵",
    "mechanist": "🟣",
    "patient_voice": "🟠",
}


def render_agent_status_cards(agent_statuses: dict) -> str:
    """Render agent status as styled HTML cards.
    
    Args:
        agent_statuses: Dict mapping role to status dict with:
            - status: "pending", "thinking", or "done"
            - model: Model name string
            - confidence: Optional confidence value
            
    Returns:
        HTML string for agent status cards.
    """
    cards_html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin-top: 1rem;">'
    for role, info in agent_statuses.items():
        color = ROLE_COLORS.get(role, "#64748b")
        emoji = ROLE_EMOJIS.get(role, "⚪")
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


def render_progress_header(
    round_state: dict,
    topology_name: str,
    topology_desc: str,
) -> str:
    """Render the progress header with round indicator.
    
    Args:
        round_state: Dict with current, total, and phase keys.
        topology_name: Display name for the topology.
        topology_desc: Description of the topology.
        
    Returns:
        HTML string for the progress header.
    """
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


def render_dialogue_entries(dialogue_entries: list) -> str:
    """Render dialogue entries as HTML.
    
    Args:
        dialogue_entries: List of dialogue entry dicts with:
            - role, display_name, content, round, color, emoji
            
    Returns:
        HTML string for dialogue display.
    """
    if not dialogue_entries:
        return (
            '<p style="color: var(--text-muted); font-style: italic; text-align: center; padding: 1rem;">'
            'Agent responses will appear here as they complete...</p>'
        )
    
    html_parts = [
        # Scrollable container
        '<div style="max-height: 500px; overflow-y: auto; padding-right: 0.5rem;">'
    ]
    current_round = 0
    for entry in dialogue_entries:
        # Add round separator if new round
        if entry["round"] != current_round:
            current_round = entry["round"]
            html_parts.append(
                f'<div style="text-align: center; margin: 1rem 0; color: var(--text-muted); font-size: 0.8rem; position: sticky; top: 0; background: var(--bg-primary); padding: 0.5rem 0; z-index: 1;">'
                f'<span style="background: var(--bg-tertiary); padding: 4px 12px; border-radius: 4px;">Round {current_round}</span></div>'
            )
        
        # Show full content, not truncated preview
        html_parts.append(
            f'<div style="background: var(--bg-secondary); border-left: 3px solid {entry["color"]}; '
            f'border-radius: 0 8px 8px 0; padding: 0.75rem 1rem; margin-bottom: 0.75rem;">'
            f'<div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">'
            f'<span style="font-weight: 600; color: {entry["color"]};">{entry["emoji"]} {entry["display_name"]}</span>'
            f'</div>'
            f'<div style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap;">{html.escape(entry["content"])}</div>'
            f'</div>'
        )
    
    html_parts.append('</div>')  # Close scrollable container
    return "".join(html_parts)


def create_log_message(message: str) -> str:
    """Create a styled log message with timestamp.
    
    Args:
        message: The log message text.
        
    Returns:
        HTML string for the log entry.
    """
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    return (
        f'<div style="display: flex; gap: 0.75rem; padding: 0.25rem 0; '
        f'border-left: 2px solid var(--bg-tertiary); padding-left: 0.75rem;">'
        f'<span style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted);">{timestamp}</span>'
        f'<span style="color: var(--text-secondary); font-size: 0.9rem;">{message}</span></div>'
    )


def get_topology_info(topology: str) -> tuple[str, str]:
    """Get display name and description for a topology.
    
    Args:
        topology: The topology identifier string.
        
    Returns:
        Tuple of (display_name, description).
    """
    topology_names = {
        "free_discussion": ("Free Discussion", "All agents deliberate openly"),
        "oxford_debate": ("Oxford Debate", "Structured proposition vs opposition"),
        "delphi_method": ("Delphi Method", "Anonymous iterative consensus"),
        "socratic_spiral": ("Socratic Spiral", "Question-driven exploration"),
        "red_team_blue_team": ("Red Team / Blue Team", "Adversarial challenge & defense"),
    }
    return topology_names.get(topology, ("Conference", "Multi-agent deliberation"))

