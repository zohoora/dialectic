"""Tests for Agent class."""

import pytest

from src.conference.agent import Agent
from src.llm.client import MockLLMClient
from src.models.conference import AgentConfig, AgentRole


class TestAgent:
    """Tests for Agent class."""

    def _create_agent(
        self,
        role: AgentRole = AgentRole.ADVOCATE,
        model: str = "test/model",
        responses: dict = None,
    ) -> tuple[Agent, MockLLMClient]:
        """Helper to create an agent with mock client."""
        config = AgentConfig(
            agent_id=f"test_{role.value}",
            role=role,
            model=model,
            temperature=0.7,
        )
        client = MockLLMClient(responses=responses or {})
        agent = Agent(config, client)
        return agent, client

    def test_agent_properties(self):
        """Test agent property accessors."""
        agent, _ = self._create_agent(
            role=AgentRole.SKEPTIC,
            model="anthropic/claude-3.5-sonnet",
        )
        
        assert agent.agent_id == "test_skeptic"
        assert agent.role == AgentRole.SKEPTIC
        assert agent.model == "anthropic/claude-3.5-sonnet"

    def test_agent_loads_system_prompt(self):
        """Test that agent loads role-specific system prompt."""
        agent, _ = self._create_agent(role=AgentRole.ADVOCATE)
        
        assert "The Advocate" in agent.system_prompt
        assert "strongest possible case" in agent.system_prompt

    @pytest.mark.asyncio
    async def test_respond_to_query(self):
        """Test agent responding to initial query."""
        agent, client = self._create_agent(
            responses={"test/model": "This is my analysis of the case."}
        )
        
        response = await agent.respond_to_query("What treatment is best?")
        
        assert response.agent_id == "test_advocate"
        assert response.role == AgentRole.ADVOCATE
        assert "analysis" in response.content
        assert response.changed_from_previous is False

    @pytest.mark.asyncio
    async def test_respond_to_query_uses_correct_model(self):
        """Test that agent uses configured model."""
        agent, client = self._create_agent(model="specific/model")
        
        await agent.respond_to_query("Test query")
        
        assert len(client.calls) == 1
        assert client.calls[0]["model"] == "specific/model"

    @pytest.mark.asyncio
    async def test_respond_to_query_uses_system_prompt(self):
        """Test that agent includes system prompt in messages."""
        agent, client = self._create_agent(role=AgentRole.EMPIRICIST)
        
        await agent.respond_to_query("Test query")
        
        messages = client.calls[0]["messages"]
        assert messages[0]["role"] == "system"
        assert "The Empiricist" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_respond_to_discussion(self):
        """Test agent responding to ongoing discussion."""
        agent, client = self._create_agent(
            responses={"test/model": "After reviewing the other positions..."}
        )
        
        previous = {
            "advocate": "I recommend treatment A.",
            "skeptic": "I have concerns about treatment A.",
        }
        
        response = await agent.respond_to_discussion(
            query="What treatment is best?",
            previous_responses=previous,
            round_number=2,
        )
        
        assert response.agent_id == "test_advocate"
        
        # Should include other agents' responses in prompt
        user_prompt = client.calls[0]["messages"][1]["content"]
        assert "treatment A" in user_prompt
        assert "Advocate" in user_prompt
        assert "Skeptic" in user_prompt

    @pytest.mark.asyncio
    async def test_detect_position_change(self):
        """Test detection of position changes."""
        agent, client = self._create_agent(
            responses={"test/model": "**Position Changed**: I now agree with the skeptic."}
        )
        
        response = await agent.respond_to_discussion(
            query="Test",
            previous_responses={"other": "Some response"},
            round_number=2,
        )
        
        assert response.changed_from_previous is True

    @pytest.mark.asyncio
    async def test_no_position_change_detected(self):
        """Test that position change is not falsely detected."""
        agent, client = self._create_agent(
            responses={"test/model": "I maintain my original position."}
        )
        
        response = await agent.respond_to_discussion(
            query="Test",
            previous_responses={"other": "Some response"},
            round_number=2,
        )
        
        assert response.changed_from_previous is False

    @pytest.mark.asyncio
    async def test_extract_position_summary(self):
        """Test extraction of position summary."""
        agent, client = self._create_agent(
            responses={
                "test/model": """
                Some analysis here.
                
                **Position Summary**: Recommend treatment A for this patient.
                """
            }
        )
        
        response = await agent.respond_to_query("Test")
        
        assert "Recommend treatment A" in response.position_summary

    @pytest.mark.asyncio
    async def test_extract_high_confidence(self):
        """Test extraction of high confidence level."""
        agent, client = self._create_agent(
            responses={
                "test/model": """
                My analysis.
                
                **Confidence Level**: High - strong evidence supports this.
                """
            }
        )
        
        response = await agent.respond_to_query("Test")
        
        assert response.confidence == 0.85

    @pytest.mark.asyncio
    async def test_extract_low_confidence(self):
        """Test extraction of low confidence level."""
        agent, client = self._create_agent(
            responses={
                "test/model": """
                My analysis.
                
                **Confidence Level**: Low - limited evidence available.
                """
            }
        )
        
        response = await agent.respond_to_query("Test")
        
        assert response.confidence == 0.35

    @pytest.mark.asyncio
    async def test_default_confidence(self):
        """Test default confidence when not specified."""
        agent, client = self._create_agent(
            responses={"test/model": "Simple response without confidence."}
        )
        
        response = await agent.respond_to_query("Test")
        
        assert response.confidence == 0.5

    @pytest.mark.asyncio
    async def test_token_tracking(self):
        """Test that token usage is tracked."""
        agent, client = self._create_agent()
        
        response = await agent.respond_to_query("Test query with some content")
        
        # MockLLMClient simulates tokens as len/4
        assert response.input_tokens > 0
        assert response.output_tokens > 0

    @pytest.mark.asyncio
    async def test_temperature_passed_to_client(self):
        """Test that configured temperature is used."""
        config = AgentConfig(
            agent_id="test",
            role=AgentRole.ADVOCATE,
            model="test/model",
            temperature=0.3,  # Custom temperature
        )
        client = MockLLMClient()
        agent = Agent(config, client)
        
        await agent.respond_to_query("Test")
        
        assert client.calls[0]["temperature"] == 0.3


class TestAgentRoles:
    """Test that all roles can be instantiated."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("role", [
        AgentRole.ADVOCATE,
        AgentRole.SKEPTIC,
        AgentRole.EMPIRICIST,
    ])
    async def test_role_can_be_created(self, role):
        """Test that each role can create an agent."""
        config = AgentConfig(
            agent_id=f"test_{role.value}",
            role=role,
            model="test/model",
        )
        client = MockLLMClient()
        agent = Agent(config, client)
        
        # Should load the appropriate prompt
        assert role.value in agent.system_prompt.lower() or \
               role.value.replace("_", " ") in agent.system_prompt.lower()

