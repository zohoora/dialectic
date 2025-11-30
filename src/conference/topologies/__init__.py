"""
Conference Topologies - Different structures for agent deliberation.

Each topology implements a different pattern of interaction between agents:
- FREE_DISCUSSION: All agents see all responses, respond freely
- OXFORD_DEBATE: Two agents argue opposing positions, third judges
- DELPHI_METHOD: Anonymous rounds, agents don't know who said what
- SOCRATIC_SPIRAL: First round is questions only, surfacing assumptions
- RED_TEAM_BLUE_TEAM: One builds proposal, other attacks it
"""

from src.conference.topologies.base import BaseTopology, TopologyFactory
from src.conference.topologies.free_discussion import FreeDiscussionTopology
from src.conference.topologies.oxford_debate import OxfordDebateTopology
from src.conference.topologies.delphi_method import DelphiMethodTopology
from src.conference.topologies.socratic_spiral import SocraticSpiralTopology
from src.conference.topologies.red_team import RedTeamBlueTeamTopology

__all__ = [
    "BaseTopology",
    "TopologyFactory",
    "FreeDiscussionTopology",
    "OxfordDebateTopology",
    "DelphiMethodTopology",
    "SocraticSpiralTopology",
    "RedTeamBlueTeamTopology",
]

