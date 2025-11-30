"""
Tests for conference topologies.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.conference.topologies.base import BaseTopology, TopologyFactory, ProgressStage, ProgressUpdate
from src.conference.topologies.free_discussion import FreeDiscussionTopology
from src.conference.topologies.oxford_debate import OxfordDebateTopology
from src.conference.topologies.delphi_method import DelphiMethodTopology
from src.conference.topologies.socratic_spiral import SocraticSpiralTopology
from src.conference.topologies.red_team import RedTeamBlueTeamTopology
from src.conference.agent import Agent
from src.models.conference import (
    AgentConfig,
    AgentResponse,
    AgentRole,
    ConferenceRound,
    ConferenceTopology,
)


class TestTopologyFactory:
    """Tests for TopologyFactory."""
    
    def create_mock_agents(self, roles: list[str]) -> list[Agent]:
        """Create mock agents for testing."""
        agents = []
        for role in roles:
            config = AgentConfig(
                agent_id=f"agent_{role}",
                role=AgentRole(role),
                model="test/model",
                temperature=0.7,
            )
            mock_client = MagicMock()
            agent = Agent(config, mock_client)
            agents.append(agent)
        return agents
    
    def test_create_free_discussion(self):
        """Test creating Free Discussion topology."""
        agents = self.create_mock_agents(["advocate", "skeptic", "empiricist"])
        topology = TopologyFactory.create(ConferenceTopology.FREE_DISCUSSION, agents)
        
        assert isinstance(topology, FreeDiscussionTopology)
        assert topology.name == "Free Discussion"
    
    def test_create_oxford_debate(self):
        """Test creating Oxford Debate topology."""
        agents = self.create_mock_agents(["advocate", "skeptic", "empiricist"])
        topology = TopologyFactory.create(ConferenceTopology.OXFORD_DEBATE, agents)
        
        assert isinstance(topology, OxfordDebateTopology)
        assert topology.name == "Oxford Debate"
    
    def test_create_delphi_method(self):
        """Test creating Delphi Method topology."""
        agents = self.create_mock_agents(["advocate", "skeptic"])
        topology = TopologyFactory.create(ConferenceTopology.DELPHI_METHOD, agents)
        
        assert isinstance(topology, DelphiMethodTopology)
        assert topology.name == "Delphi Method"
    
    def test_create_socratic_spiral(self):
        """Test creating Socratic Spiral topology."""
        agents = self.create_mock_agents(["advocate", "skeptic"])
        topology = TopologyFactory.create(ConferenceTopology.SOCRATIC_SPIRAL, agents)
        
        assert isinstance(topology, SocraticSpiralTopology)
        assert topology.name == "Socratic Spiral"
        assert topology.minimum_rounds == 3
    
    def test_create_red_team_blue_team(self):
        """Test creating Red Team / Blue Team topology."""
        agents = self.create_mock_agents(["advocate", "skeptic", "empiricist"])
        topology = TopologyFactory.create(ConferenceTopology.RED_TEAM_BLUE_TEAM, agents)
        
        assert isinstance(topology, RedTeamBlueTeamTopology)
        assert topology.name == "Red Team / Blue Team"
    
    def test_oxford_debate_requires_advocate_skeptic(self):
        """Test that Oxford Debate requires advocate and skeptic roles."""
        # Missing skeptic
        agents = self.create_mock_agents(["advocate", "empiricist"])
        
        with pytest.raises(ValueError) as exc_info:
            TopologyFactory.create(ConferenceTopology.OXFORD_DEBATE, agents)
        
        assert "Missing required roles" in str(exc_info.value)
    
    def test_red_team_requires_advocate_skeptic(self):
        """Test that Red Team requires advocate and skeptic roles."""
        # Missing advocate
        agents = self.create_mock_agents(["skeptic", "empiricist"])
        
        with pytest.raises(ValueError) as exc_info:
            TopologyFactory.create(ConferenceTopology.RED_TEAM_BLUE_TEAM, agents)
        
        assert "Missing required roles" in str(exc_info.value)


class TestFreeDiscussionTopology:
    """Tests for Free Discussion topology."""
    
    @pytest.fixture
    def mock_agents(self):
        """Create mock agents."""
        agents = []
        roles = ["advocate", "skeptic", "empiricist"]
        
        for role in roles:
            config = AgentConfig(
                agent_id=f"agent_{role}",
                role=AgentRole(role),
                model="test/model",
                temperature=0.7,
            )
            mock_client = MagicMock()
            agent = Agent(config, mock_client)
            
            # Mock respond methods
            async def mock_respond(*args, **kwargs):
                return AgentResponse(
                    agent_id=config.agent_id,
                    role=AgentRole(role),
                    model="test/model",
                    content="Test response",
                    confidence=0.8,
                )
            
            agent.respond_to_query = AsyncMock(side_effect=mock_respond)
            agent.respond_to_discussion = AsyncMock(side_effect=mock_respond)
            agents.append(agent)
        
        return agents
    
    @pytest.mark.asyncio
    async def test_execute_round_one(self, mock_agents):
        """Test executing round 1 in free discussion."""
        topology = FreeDiscussionTopology(mock_agents)
        
        result = await topology.execute_round(
            query="Test query",
            round_number=1,
            previous_rounds=[],
        )
        
        assert isinstance(result, ConferenceRound)
        assert result.round_number == 1
        assert len(result.agent_responses) == 3
        
        # All agents should have used respond_to_query
        for agent in mock_agents:
            agent.respond_to_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_round_two(self, mock_agents):
        """Test executing round 2 in free discussion."""
        topology = FreeDiscussionTopology(mock_agents)
        
        # Create mock previous round
        round_one = ConferenceRound(
            round_number=1,
            agent_responses={
                agent.agent_id: AgentResponse(
                    agent_id=agent.agent_id,
                    role=AgentRole(agent.role),
                    model="test/model",
                    content="Round 1 response",
                    confidence=0.8,
                )
                for agent in mock_agents
            },
        )
        
        result = await topology.execute_round(
            query="Test query",
            round_number=2,
            previous_rounds=[round_one],
        )
        
        assert result.round_number == 2
        
        # All agents should have used respond_to_discussion
        for agent in mock_agents:
            agent.respond_to_discussion.assert_called_once()


class TestOxfordDebateTopology:
    """Tests for Oxford Debate topology."""
    
    @pytest.fixture
    def debate_agents(self):
        """Create agents for debate."""
        agents = []
        roles = ["advocate", "skeptic", "empiricist"]
        
        for role in roles:
            config = AgentConfig(
                agent_id=f"agent_{role}",
                role=AgentRole(role),
                model="test/model",
                temperature=0.7,
            )
            mock_client = MagicMock()
            agent = Agent(config, mock_client)
            
            async def mock_respond(*args, _role=role, **kwargs):
                return AgentResponse(
                    agent_id=f"agent_{_role}",
                    role=AgentRole(_role),
                    model="test/model",
                    content=f"Response from {_role}",
                    confidence=0.8,
                )
            
            agent.respond_to_query = AsyncMock(side_effect=mock_respond)
            agent.respond_to_discussion = AsyncMock(side_effect=mock_respond)
            agents.append(agent)
        
        return agents
    
    @pytest.mark.asyncio
    async def test_debate_round_one(self, debate_agents):
        """Test first round of debate."""
        topology = OxfordDebateTopology(debate_agents)
        
        result = await topology.execute_round(
            query="Is treatment A better than B?",
            round_number=1,
            previous_rounds=[],
        )
        
        assert result.round_number == 1
        # Should have responses from advocate, skeptic, and judge
        assert len(result.agent_responses) == 3
    
    def test_required_roles(self, debate_agents):
        """Test that debate requires advocate and skeptic."""
        topology = OxfordDebateTopology(debate_agents)
        assert "advocate" in topology.required_roles
        assert "skeptic" in topology.required_roles


class TestDelphiMethodTopology:
    """Tests for Delphi Method topology."""
    
    @pytest.fixture
    def panel_agents(self):
        """Create panel agents."""
        agents = []
        roles = ["advocate", "skeptic", "empiricist"]
        
        for role in roles:
            config = AgentConfig(
                agent_id=f"agent_{role}",
                role=AgentRole(role),
                model="test/model",
                temperature=0.7,
            )
            mock_client = MagicMock()
            agent = Agent(config, mock_client)
            
            async def mock_respond(*args, **kwargs):
                return AgentResponse(
                    agent_id=config.agent_id,
                    role=AgentRole(role),
                    model="test/model",
                    content="Anonymous response",
                    confidence=0.8,
                )
            
            agent.respond_to_query = AsyncMock(side_effect=mock_respond)
            agent.respond_to_discussion = AsyncMock(side_effect=mock_respond)
            agents.append(agent)
        
        return agents
    
    def test_anonymize_responses(self, panel_agents):
        """Test that responses are properly anonymized."""
        topology = DelphiMethodTopology(panel_agents)
        
        responses = {
            "agent_advocate": AgentResponse(
                agent_id="agent_advocate",
                role=AgentRole.ADVOCATE,
                model="test",
                content="As the Advocate, I recommend X",
                confidence=0.9,
            ),
            "agent_skeptic": AgentResponse(
                agent_id="agent_skeptic",
                role=AgentRole.SKEPTIC,
                model="test",
                content="I disagree with X",
                confidence=0.7,
            ),
        }
        
        anonymized = topology._anonymize_responses(responses)
        
        # Should have panelist labels
        assert all(key.startswith("Panelist") for key in anonymized.keys())
        # Should have replaced "As the Advocate" with "As a panelist"
        assert "As the Advocate" not in str(anonymized.values())


class TestSocraticSpiralTopology:
    """Tests for Socratic Spiral topology."""
    
    @pytest.fixture
    def socratic_agents(self):
        """Create agents for Socratic dialogue."""
        agents = []
        
        for role in ["advocate", "skeptic"]:
            config = AgentConfig(
                agent_id=f"agent_{role}",
                role=AgentRole(role),
                model="test/model",
                temperature=0.7,
            )
            mock_client = MagicMock()
            agent = Agent(config, mock_client)
            
            async def mock_respond(*args, **kwargs):
                return AgentResponse(
                    agent_id=config.agent_id,
                    role=AgentRole(role),
                    model="test/model",
                    content="Response",
                    confidence=0.8,
                )
            
            agent.respond_to_query = AsyncMock(side_effect=mock_respond)
            agent.respond_to_discussion = AsyncMock(side_effect=mock_respond)
            agents.append(agent)
        
        return agents
    
    def test_minimum_rounds_is_three(self, socratic_agents):
        """Test that Socratic Spiral requires at least 3 rounds."""
        topology = SocraticSpiralTopology(socratic_agents)
        assert topology.minimum_rounds == 3
    
    def test_round_framing(self, socratic_agents):
        """Test that different rounds get different framing."""
        topology = SocraticSpiralTopology(socratic_agents)
        
        r1 = topology._get_round_framing(1, "advocate")
        r2 = topology._get_round_framing(2, "advocate")
        r3 = topology._get_round_framing(3, "advocate")
        
        assert "Questions Only" in r1
        assert "Answering Questions" in r2
        assert "Building on Insights" in r3


class TestRedTeamBlueTeamTopology:
    """Tests for Red Team / Blue Team topology."""
    
    @pytest.fixture
    def team_agents(self):
        """Create team agents."""
        agents = []
        
        for role in ["advocate", "skeptic", "empiricist"]:
            config = AgentConfig(
                agent_id=f"agent_{role}",
                role=AgentRole(role),
                model="test/model",
                temperature=0.7,
            )
            mock_client = MagicMock()
            agent = Agent(config, mock_client)
            
            async def mock_respond(*args, _r=role, **kwargs):
                return AgentResponse(
                    agent_id=f"agent_{_r}",
                    role=AgentRole(_r),
                    model="test/model",
                    content=f"Team {_r} response",
                    confidence=0.8,
                )
            
            agent.respond_to_query = AsyncMock(side_effect=mock_respond)
            agent.respond_to_discussion = AsyncMock(side_effect=mock_respond)
            agents.append(agent)
        
        return agents
    
    def test_team_framing(self, team_agents):
        """Test team-specific framing."""
        topology = RedTeamBlueTeamTopology(team_agents)
        
        blue_r1 = topology._get_team_framing("advocate", 1, True)
        red_r1 = topology._get_team_framing("skeptic", 1, False)
        
        assert "BLUE TEAM" in blue_r1
        assert "PROPOSAL" in blue_r1
        assert "RED TEAM" in red_r1
        assert "ATTACK" in red_r1
    
    def test_required_roles(self, team_agents):
        """Test required roles."""
        topology = RedTeamBlueTeamTopology(team_agents)
        assert "advocate" in topology.required_roles
        assert "skeptic" in topology.required_roles


class TestProgressCallbacks:
    """Test progress callback handling across topologies."""
    
    @pytest.fixture
    def mock_agents(self):
        """Create minimal mock agents."""
        agents = []
        
        for role in ["advocate", "skeptic"]:
            config = AgentConfig(
                agent_id=f"agent_{role}",
                role=AgentRole(role),
                model="test/model",
                temperature=0.7,
            )
            mock_client = MagicMock()
            agent = Agent(config, mock_client)
            
            async def mock_respond(*args, _role=role, **kwargs):
                return AgentResponse(
                    agent_id=f"agent_{_role}",
                    role=AgentRole(_role),
                    model="test/model",
                    content="Response",
                    confidence=0.8,
                )
            
            agent.respond_to_query = AsyncMock(side_effect=mock_respond)
            agent.respond_to_discussion = AsyncMock(side_effect=mock_respond)
            agents.append(agent)
        
        return agents
    
    @pytest.mark.asyncio
    async def test_progress_callbacks_called(self, mock_agents):
        """Test that progress callbacks are properly invoked."""
        topology = FreeDiscussionTopology(mock_agents)
        
        progress_updates = []
        
        def callback(update: ProgressUpdate):
            progress_updates.append(update)
        
        await topology.execute_round(
            query="Test",
            round_number=1,
            previous_rounds=[],
            progress_callback=callback,
        )
        
        # Should have AGENT_THINKING and AGENT_COMPLETE for each agent
        thinking_updates = [u for u in progress_updates if u.stage == ProgressStage.AGENT_THINKING]
        complete_updates = [u for u in progress_updates if u.stage == ProgressStage.AGENT_COMPLETE]
        
        assert len(thinking_updates) == 2
        assert len(complete_updates) == 2

