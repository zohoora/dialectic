"""
Tests for Shadow Mode (counterfactual evaluation).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.models.shadow import (
    JudgeScores,
    Preference,
    ShadowBatch,
    ShadowInsight,
    ShadowResult,
    ShadowSummary,
)
from src.models.conference import (
    AgentConfig,
    AgentRole,
    ArbitratorConfig,
    ConferenceConfig,
    ConferenceResult,
    ConferenceSynthesis,
    DissentRecord,
    TokenUsage,
)
from src.shadow.runner import ConferenceJudge, ShadowRunner


# ==============================================================================
# Test Shadow Data Models
# ==============================================================================

class TestJudgeScores:
    """Tests for JudgeScores model."""
    
    def test_create_scores(self):
        """Test creating judge scores."""
        scores = JudgeScores(
            accuracy=8,
            evidence=7,
            calibration=6,
            actionability=9,
            safety=8,
            overall_preference=Preference.ALTERNATIVE,
        )
        
        assert scores.accuracy == 8
        assert scores.overall_preference == Preference.ALTERNATIVE
    
    def test_total_score(self):
        """Test weighted total score calculation."""
        scores = JudgeScores(
            accuracy=10,
            evidence=10,
            calibration=10,
            actionability=10,
            safety=10,
            overall_preference=Preference.ALTERNATIVE,
        )
        
        assert scores.total_score == 10.0
    
    def test_is_better(self):
        """Test is_better property."""
        better = JudgeScores(
            accuracy=8, evidence=8, calibration=8, actionability=8, safety=8,
            overall_preference=Preference.ALTERNATIVE,
        )
        
        worse = JudgeScores(
            accuracy=8, evidence=8, calibration=8, actionability=8, safety=8,
            overall_preference=Preference.ORIGINAL,
        )
        
        assert better.is_better is True
        assert worse.is_better is False


class TestShadowResult:
    """Tests for ShadowResult model."""
    
    def test_create_result(self):
        """Test creating shadow result."""
        scores = JudgeScores(
            accuracy=7, evidence=7, calibration=7, actionability=7, safety=7,
            overall_preference=Preference.TIE,
        )
        
        result = ShadowResult(
            shadow_id="shadow_123",
            original_conference_id="conf_456",
            config_signature="2:model-a:model-b",
            synthesis="Alternative synthesis...",
            scores=scores,
            duration_ms=5000,
        )
        
        assert result.shadow_id == "shadow_123"
        assert abs(result.scores.total_score - 7.0) < 0.001  # Float comparison


class TestShadowBatch:
    """Tests for ShadowBatch model."""
    
    def test_create_batch(self):
        """Test creating shadow batch."""
        batch = ShadowBatch(
            batch_id="batch_001",
            conference_ids=["conf_1", "conf_2"],
            alternative_configs=["config_a", "config_b"],
        )
        
        assert len(batch.conference_ids) == 2
        assert batch.status == "pending"
    
    def test_add_result(self):
        """Test adding result to batch."""
        batch = ShadowBatch(batch_id="batch_001")
        
        scores = JudgeScores(
            accuracy=8, evidence=8, calibration=8, actionability=8, safety=8,
            overall_preference=Preference.ALTERNATIVE,
        )
        
        result = ShadowResult(
            shadow_id="shadow_1",
            original_conference_id="conf_1",
            config_signature="config_a",
            synthesis="Test",
            scores=scores,
        )
        
        batch.add_result(result)
        
        assert batch.completed_runs == 1
        assert batch.improvements_found == 1


class TestShadowSummary:
    """Tests for ShadowSummary model."""
    
    def test_create_summary(self):
        """Test creating shadow summary."""
        summary = ShadowSummary(
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now(),
            total_shadow_runs=100,
            conferences_replayed=50,
            improvements_found=30,
            improvement_rate=0.3,
        )
        
        assert summary.total_shadow_runs == 100
        assert summary.improvement_rate == 0.3


class TestShadowInsight:
    """Tests for ShadowInsight model."""
    
    def test_create_insight(self):
        """Test creating shadow insight."""
        insight = ShadowInsight(
            insight_type="config_better",
            description="Config X outperforms in 70% of cases",
            sample_size=50,
            confidence="HIGH",
            recommendation="Use Config X",
        )
        
        assert insight.insight_type == "config_better"
        assert insight.confidence == "HIGH"


# ==============================================================================
# Test Conference Judge
# ==============================================================================

class TestConferenceJudge:
    """Tests for ConferenceJudge."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        mock = MagicMock()
        mock.complete = AsyncMock()
        return mock
    
    @pytest.fixture
    def judge(self, mock_llm):
        """Create judge with mock LLM."""
        return ConferenceJudge(mock_llm)
    
    @pytest.mark.asyncio
    async def test_evaluate_parses_response(self, judge, mock_llm):
        """Test judge evaluation parsing."""
        mock_llm.complete.return_value = MagicMock(
            content="""
            {
                "scores_a": {"accuracy": 7, "evidence": 7, "calibration": 7, "actionability": 7, "safety": 7},
                "scores_b": {"accuracy": 8, "evidence": 8, "calibration": 8, "actionability": 8, "safety": 8},
                "overall_preference": "B",
                "reasoning": "Response B is more comprehensive"
            }
            """
        )
        
        scores = await judge.evaluate(
            query="Test query",
            response_a="Response A",
            response_b="Response B",
        )
        
        assert scores.accuracy == 8
        assert scores.overall_preference == Preference.ALTERNATIVE
    
    @pytest.mark.asyncio
    async def test_evaluate_handles_parse_error(self, judge, mock_llm):
        """Test judge handles parse errors gracefully."""
        mock_llm.complete.return_value = MagicMock(content="Invalid JSON")
        
        scores = await judge.evaluate("Query", "A", "B")
        
        assert scores.accuracy == 5  # Default neutral
        assert scores.overall_preference == Preference.TIE
    
    @pytest.mark.asyncio
    async def test_evaluate_preference_a(self, judge, mock_llm):
        """Test judge parsing preference A."""
        mock_llm.complete.return_value = MagicMock(
            content='{"scores_a": {}, "scores_b": {"accuracy": 5, "evidence": 5, "calibration": 5, "actionability": 5, "safety": 5}, "overall_preference": "A"}'
        )
        
        scores = await judge.evaluate("Query", "A", "B")
        
        assert scores.overall_preference == Preference.ORIGINAL


# ==============================================================================
# Test Shadow Runner
# ==============================================================================

class TestShadowRunner:
    """Tests for ShadowRunner."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        mock = MagicMock()
        mock.complete = AsyncMock(return_value=MagicMock(
            content='{"scores_a": {}, "scores_b": {"accuracy": 7, "evidence": 7, "calibration": 7, "actionability": 7, "safety": 7}, "overall_preference": "B"}'
        ))
        return mock
    
    @pytest.fixture
    def mock_engine(self):
        """Create mock conference engine."""
        mock = MagicMock()
        mock.run_conference = AsyncMock()
        return mock
    
    @pytest.fixture
    def sample_result(self):
        """Create sample conference result."""
        return ConferenceResult(
            conference_id="conf_123",
            query="Test medical query",
            config=ConferenceConfig(
                num_rounds=2,
                agents=[AgentConfig(agent_id="a1", role=AgentRole.ADVOCATE, model="m")],
                arbitrator=ArbitratorConfig(model="arb"),
            ),
            rounds=[],
            synthesis=ConferenceSynthesis(
                final_consensus="Original recommendation...",
                confidence_score=0.8,
                areas_of_agreement=["Point 1"],
                areas_of_disagreement=[],
                key_evidence=[],
                limitations=["Limit 1"],
            ),
            dissent=DissentRecord(preserved=False, summary=""),
            token_usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            duration_ms=1000,
        )
    
    @pytest.fixture
    def alt_config(self):
        """Create alternative config."""
        return ConferenceConfig(
            num_rounds=3,
            agents=[
                AgentConfig(agent_id="a1", role=AgentRole.ADVOCATE, model="better-model"),
            ],
            arbitrator=ArbitratorConfig(model="better-arb"),
        )
    
    @pytest.mark.asyncio
    async def test_run_shadow_evaluation(self, mock_llm, mock_engine, sample_result, alt_config):
        """Test running shadow evaluation."""
        # Setup mock engine response
        mock_engine.run_conference.return_value = ConferenceResult(
            conference_id="shadow_conf",
            query="Test",
            config=alt_config,
            rounds=[],
            synthesis=ConferenceSynthesis(
                final_consensus="Alternative recommendation...",
                confidence_score=0.85,
                areas_of_agreement=["Point 1"],
                areas_of_disagreement=[],
                key_evidence=[],
                limitations=[],
            ),
            dissent=DissentRecord(preserved=False, summary=""),
            token_usage=TokenUsage(prompt_tokens=120, completion_tokens=60, total_tokens=180),
            duration_ms=1200,
        )
        
        runner = ShadowRunner(mock_llm, mock_engine)
        
        results = await runner.run_shadow_evaluation(sample_result, [alt_config])
        
        assert len(results) == 1
        assert results[0].original_conference_id == "conf_123"
        assert results[0].scores.overall_preference == Preference.ALTERNATIVE
    
    def test_get_insights_insufficient_data(self, mock_llm, mock_engine):
        """Test insights with insufficient data."""
        runner = ShadowRunner(mock_llm, mock_engine)
        
        # No results
        insights = runner.get_insights(min_samples=5)
        
        assert len(insights) == 0
    
    def test_get_summary_empty(self, mock_llm, mock_engine):
        """Test summary with no results."""
        runner = ShadowRunner(mock_llm, mock_engine)
        
        summary = runner.get_summary()
        
        assert summary.total_shadow_runs == 0
    
    def test_get_summary_with_results(self, mock_llm, mock_engine):
        """Test summary with results."""
        runner = ShadowRunner(mock_llm, mock_engine)
        
        # Add some mock results
        for i in range(5):
            scores = JudgeScores(
                accuracy=7, evidence=7, calibration=7, actionability=7, safety=7,
                overall_preference=Preference.ALTERNATIVE if i % 2 == 0 else Preference.ORIGINAL,
            )
            runner.results.append(ShadowResult(
                shadow_id=f"shadow_{i}",
                original_conference_id=f"conf_{i}",
                config_signature="test_config",
                synthesis="Test",
                scores=scores,
            ))
        
        summary = runner.get_summary()
        
        assert summary.total_shadow_runs == 5
        assert summary.improvements_found == 3  # 0, 2, 4


# ==============================================================================
# Test Preference Enum
# ==============================================================================

class TestPreference:
    """Tests for Preference enum."""
    
    def test_preference_values(self):
        """Test preference enum values."""
        assert Preference.ORIGINAL.value == "original"
        assert Preference.ALTERNATIVE.value == "alternative"
        assert Preference.TIE.value == "tie"

