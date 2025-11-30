"""Tests for RoundExecutor."""

import pytest

from src.conference.agent import Agent
from src.conference.round_executor import RoundExecutor
from src.llm.client import MockLLMClient
from src.models.conference import AgentConfig, AgentRole


class TestRoundExecutor:
    """Tests for RoundExecutor class."""

    def _create_agents(self) -> tuple[list[Agent], MockLLMClient]:
        """Helper to create test agents."""
        client = MockLLMClient(responses={
            "model-advocate": "Advocate response: I recommend treatment A.\n**Position Summary**: Recommend treatment A.",
            "model-skeptic": "Skeptic response: I have concerns.\n**Position Summary**: Concerns about treatment A.",
            "model-empiricist": "Empiricist response: Evidence is limited.\n**Position Summary**: Insufficient evidence.",
        })
        
        agents = [
            Agent(
                AgentConfig(
                    agent_id="advocate",
                    role=AgentRole.ADVOCATE,
                    model="model-advocate",
                ),
                client,
            ),
            Agent(
                AgentConfig(
                    agent_id="skeptic",
                    role=AgentRole.SKEPTIC,
                    model="model-skeptic",
                ),
                client,
            ),
            Agent(
                AgentConfig(
                    agent_id="empiricist",
                    role=AgentRole.EMPIRICIST,
                    model="model-empiricist",
                ),
                client,
            ),
        ]
        
        return agents, client

    @pytest.mark.asyncio
    async def test_execute_round_one(self):
        """Test executing the first round."""
        agents, client = self._create_agents()
        executor = RoundExecutor(agents)
        
        round_result = await executor.execute_round_one("What is the best treatment?")
        
        assert round_result.round_number == 1
        assert len(round_result.agent_responses) == 3
        assert "advocate" in round_result.agent_responses
        assert "skeptic" in round_result.agent_responses
        assert "empiricist" in round_result.agent_responses

    @pytest.mark.asyncio
    async def test_round_one_responses_content(self):
        """Test that round one responses have correct content."""
        agents, client = self._create_agents()
        executor = RoundExecutor(agents)
        
        round_result = await executor.execute_round_one("Test query")
        
        advocate_response = round_result.agent_responses["advocate"]
        assert "Advocate response" in advocate_response.content
        assert advocate_response.role == AgentRole.ADVOCATE

    @pytest.mark.asyncio
    async def test_round_one_calls_all_agents(self):
        """Test that round one calls all agents."""
        agents, client = self._create_agents()
        executor = RoundExecutor(agents)
        
        await executor.execute_round_one("Test query")
        
        # Each agent should have been called once
        assert len(client.calls) == 3
        models_called = [call["model"] for call in client.calls]
        assert "model-advocate" in models_called
        assert "model-skeptic" in models_called
        assert "model-empiricist" in models_called

    @pytest.mark.asyncio
    async def test_execute_followup_round(self):
        """Test executing a follow-up round."""
        agents, client = self._create_agents()
        executor = RoundExecutor(agents)
        
        # First, run round 1
        round_one = await executor.execute_round_one("Test query")
        
        # Clear call history
        client.calls = []
        
        # Then run round 2
        round_two = await executor.execute_followup_round(
            query="Test query",
            previous_round=round_one,
            round_number=2,
        )
        
        assert round_two.round_number == 2
        assert len(round_two.agent_responses) == 3

    @pytest.mark.asyncio
    async def test_followup_round_includes_context(self):
        """Test that follow-up rounds include other agents' responses."""
        agents, client = self._create_agents()
        executor = RoundExecutor(agents)
        
        round_one = await executor.execute_round_one("Test query")
        client.calls = []
        
        await executor.execute_followup_round(
            query="Test query",
            previous_round=round_one,
            round_number=2,
        )
        
        # Check that prompts include other agents' responses
        for call in client.calls:
            user_message = call["messages"][1]["content"]
            # Each agent should see responses from at least one other agent
            assert "Advocate" in user_message or "Skeptic" in user_message or "Empiricist" in user_message

    @pytest.mark.asyncio
    async def test_execute_all_rounds(self):
        """Test executing multiple rounds."""
        agents, client = self._create_agents()
        executor = RoundExecutor(agents)
        
        rounds = await executor.execute_all_rounds(
            query="Test query",
            num_rounds=2,
        )
        
        assert len(rounds) == 2
        assert rounds[0].round_number == 1
        assert rounds[1].round_number == 2

    @pytest.mark.asyncio
    async def test_execute_three_rounds(self):
        """Test executing three rounds."""
        agents, client = self._create_agents()
        executor = RoundExecutor(agents)
        
        rounds = await executor.execute_all_rounds(
            query="Test query",
            num_rounds=3,
        )
        
        assert len(rounds) == 3
        assert rounds[2].round_number == 3

    @pytest.mark.asyncio
    async def test_convergence_summary_no_changes(self):
        """Test convergence summary with no position changes."""
        agents, client = self._create_agents()
        executor = RoundExecutor(agents)
        
        rounds = await executor.execute_all_rounds(
            query="Test query",
            num_rounds=2,
        )
        
        summary = executor.get_convergence_summary(rounds)
        
        assert "changes" in summary
        assert "num_position_changes" in summary

    @pytest.mark.asyncio
    async def test_single_round_convergence(self):
        """Test convergence summary with single round."""
        agents, client = self._create_agents()
        executor = RoundExecutor(agents)
        
        rounds = await executor.execute_all_rounds(
            query="Test query",
            num_rounds=1,
        )
        
        summary = executor.get_convergence_summary(rounds)
        
        assert summary["converged"] is True
        assert summary["changes"] == []


class TestRoundExecutorEdgeCases:
    """Edge case tests for RoundExecutor."""

    @pytest.mark.asyncio
    async def test_single_agent(self):
        """Test with a single agent."""
        client = MockLLMClient()
        agent = Agent(
            AgentConfig(
                agent_id="solo",
                role=AgentRole.ADVOCATE,
                model="test",
            ),
            client,
        )
        
        executor = RoundExecutor([agent])
        
        round_result = await executor.execute_round_one("Test query")
        
        assert len(round_result.agent_responses) == 1
        assert "solo" in round_result.agent_responses

    @pytest.mark.asyncio
    async def test_two_agents(self):
        """Test with two agents."""
        client = MockLLMClient()
        agents = [
            Agent(
                AgentConfig(
                    agent_id="agent1",
                    role=AgentRole.ADVOCATE,
                    model="test",
                ),
                client,
            ),
            Agent(
                AgentConfig(
                    agent_id="agent2",
                    role=AgentRole.SKEPTIC,
                    model="test",
                ),
                client,
            ),
        ]
        
        executor = RoundExecutor(agents)
        
        rounds = await executor.execute_all_rounds("Test", num_rounds=2)
        
        assert len(rounds[0].agent_responses) == 2
        assert len(rounds[1].agent_responses) == 2

