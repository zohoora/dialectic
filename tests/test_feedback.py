"""
Tests for the Feedback & Optimization system.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from src.models.feedback import (
    ComponentEffect,
    ConferenceFeedback,
    DelayedFeedback,
    FeedbackSignal,
    ImmediateFeedback,
    QueryClassification,
    SignalType,
    SIGNAL_WEIGHTS,
)
from src.models.conference import AgentConfig, AgentRole, ArbitratorConfig, ConferenceConfig
from src.learning.optimizer import (
    ConfigurationOptimizer,
    FeedbackCollector,
    get_decayed_weight,
    HALF_LIVES_MONTHS,
)


# ==============================================================================
# Test Feedback Models
# ==============================================================================

class TestFeedbackSignal:
    """Tests for FeedbackSignal model."""
    
    def test_create_signal(self):
        """Test creating a feedback signal."""
        signal = FeedbackSignal(
            signal_type=SignalType.THUMBS_UP,
            value=1.0,
        )
        
        assert signal.signal_type == SignalType.THUMBS_UP
        assert signal.value == 1.0
        assert signal.weight == SIGNAL_WEIGHTS[SignalType.THUMBS_UP]
    
    def test_signal_weights_defined(self):
        """Test that all signal types have weights defined."""
        for signal_type in SignalType:
            assert signal_type in SIGNAL_WEIGHTS


class TestImmediateFeedback:
    """Tests for ImmediateFeedback model."""
    
    def test_to_signals_useful_yes(self):
        """Test converting useful=yes to signals."""
        feedback = ImmediateFeedback(useful="yes")
        signals = feedback.to_signals()
        
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.THUMBS_UP
    
    def test_to_signals_will_act(self):
        """Test converting will_act to signals."""
        feedback = ImmediateFeedback(will_act="modified")
        signals = feedback.to_signals()
        
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.ACTED_ON_MODIFIED
    
    def test_to_signals_multiple(self):
        """Test converting multiple fields to signals."""
        feedback = ImmediateFeedback(
            useful="yes",
            will_act="yes",
            dissent_useful=True,
        )
        signals = feedback.to_signals()
        
        assert len(signals) == 3


class TestDelayedFeedback:
    """Tests for DelayedFeedback model."""
    
    def test_to_signals_worked(self):
        """Test converting outcome=worked to signals."""
        feedback = DelayedFeedback(outcome="worked")
        signals = feedback.to_signals()
        
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.DELAYED_WORKED
    
    def test_to_signals_adverse(self):
        """Test converting adverse outcome to signals."""
        feedback = DelayedFeedback(outcome="adverse", details="Patient had reaction")
        signals = feedback.to_signals()
        
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.DELAYED_ADVERSE


class TestConferenceFeedback:
    """Tests for ConferenceFeedback model."""
    
    def test_create_feedback(self):
        """Test creating conference feedback."""
        fb = ConferenceFeedback(conference_id="conf_123")
        
        assert fb.conference_id == "conf_123"
        assert fb.signals == []
        assert fb.outcome_score is None
    
    def test_add_signal_computes_outcome(self):
        """Test that adding signals recomputes outcome."""
        fb = ConferenceFeedback(conference_id="conf_123")
        fb.add_signal(FeedbackSignal(signal_type=SignalType.THUMBS_UP))
        
        assert fb.outcome_score is not None
        assert fb.outcome_score > 0.5  # Positive signal
    
    def test_outcome_computation_mixed(self):
        """Test outcome computation with mixed signals."""
        fb = ConferenceFeedback(conference_id="conf_123")
        fb.add_signal(FeedbackSignal(signal_type=SignalType.THUMBS_UP))
        fb.add_signal(FeedbackSignal(signal_type=SignalType.THUMBS_DOWN))
        
        # Mixed signals should be near neutral
        assert 0.3 < fb.outcome_score < 0.7
    
    def test_add_immediate(self):
        """Test adding immediate feedback."""
        fb = ConferenceFeedback(conference_id="conf_123")
        fb.add_immediate(ImmediateFeedback(useful="yes", will_act="yes"))
        
        assert fb.immediate is not None
        assert len(fb.signals) == 2
    
    def test_add_delayed(self):
        """Test adding delayed feedback."""
        fb = ConferenceFeedback(conference_id="conf_123")
        fb.add_delayed(DelayedFeedback(outcome="worked"))
        
        assert fb.delayed is not None
        assert fb.outcome_score is not None


class TestQueryClassification:
    """Tests for QueryClassification model."""
    
    def test_signature(self):
        """Test creating signature."""
        qc = QueryClassification(
            query_type="diagnostic",
            domain="cardiology",
            complexity="high",
        )
        
        assert qc.signature() == "diagnostic:cardiology:high"


# ==============================================================================
# Test Time Decay
# ==============================================================================

class TestTimeDecay:
    """Tests for time-weighted decay."""
    
    def test_no_decay_recent(self):
        """Test that recent observations have weight near 1."""
        weight = get_decayed_weight(datetime.now())
        assert weight > 0.99
    
    def test_half_decay_at_half_life(self):
        """Test that weight is ~0.5 at half-life."""
        half_life = HALF_LIVES_MONTHS["model_performance"]
        old_date = datetime.now() - timedelta(days=half_life * 30)
        
        weight = get_decayed_weight(old_date, "model_performance")
        assert 0.45 < weight < 0.55
    
    def test_heavy_decay_old(self):
        """Test that very old observations have low weight."""
        very_old = datetime.now() - timedelta(days=365 * 2)  # 2 years
        weight = get_decayed_weight(very_old, "model_performance")
        
        assert weight < 0.1


# ==============================================================================
# Test Configuration Optimizer
# ==============================================================================

class TestConfigurationOptimizer:
    """Tests for ConfigurationOptimizer."""
    
    @pytest.fixture
    def optimizer(self):
        """Create an in-memory optimizer."""
        return ConfigurationOptimizer()
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample conference config."""
        return ConferenceConfig(
            num_rounds=2,
            agents=[
                AgentConfig(agent_id="adv", role=AgentRole.ADVOCATE, model="model-a"),
                AgentConfig(agent_id="skp", role=AgentRole.SKEPTIC, model="model-b"),
            ],
            arbitrator=ArbitratorConfig(model="model-c"),
        )
    
    @pytest.fixture
    def query_class(self):
        """Create a sample query classification."""
        return QueryClassification(
            query_type="diagnostic",
            domain="cardiology",
        )
    
    def test_select_single_config(self, optimizer, sample_config, query_class):
        """Test selecting when only one config available."""
        selected = optimizer.select_configuration(query_class, [sample_config])
        assert selected == sample_config
    
    def test_select_from_multiple(self, optimizer, query_class):
        """Test selecting from multiple configs."""
        configs = [
            ConferenceConfig(
                num_rounds=i,
                agents=[AgentConfig(agent_id="a", role=AgentRole.ADVOCATE, model="m")],
                arbitrator=ArbitratorConfig(model="arb"),
            )
            for i in range(1, 4)
        ]
        
        selected = optimizer.select_configuration(query_class, configs)
        assert selected in configs
    
    def test_update_creates_posterior(self, optimizer, sample_config, query_class):
        """Test that update creates posterior entry."""
        optimizer.update(query_class, sample_config, 0.8)
        
        assert len(optimizer.posteriors) > 0
        assert len(optimizer.observations) == 1
    
    def test_update_modifies_posterior(self, optimizer, sample_config, query_class):
        """Test that multiple updates modify posterior."""
        sig = optimizer._config_signature(sample_config)
        key = f"{query_class.signature()}:{sig}"
        
        # Initial state
        optimizer.update(query_class, sample_config, 0.8)
        initial_alpha = optimizer.posteriors[key]["alpha"]
        initial_beta = optimizer.posteriors[key]["beta"]
        
        # After more updates, total should increase
        for _ in range(10):
            optimizer.update(query_class, sample_config, 0.7)
        
        final_alpha = optimizer.posteriors[key]["alpha"]
        final_beta = optimizer.posteriors[key]["beta"]
        
        assert (final_alpha + final_beta) > (initial_alpha + initial_beta)
    
    def test_component_attribution(self, optimizer, sample_config, query_class):
        """Test that component effects are tracked."""
        optimizer.update(query_class, sample_config, 0.9)
        
        assert len(optimizer.component_effects) > 0
        
        # Check a specific component
        effect = optimizer.get_component_effect(
            query_class.query_type,
            "num_rounds",
            str(sample_config.num_rounds),
        )
        assert effect.sample_size == 1
    
    def test_get_insights(self, optimizer, sample_config, query_class):
        """Test getting optimization insights."""
        # Add some data
        for _ in range(5):
            optimizer.update(query_class, sample_config, 0.8)
        
        insights = optimizer.get_insights(query_class.query_type)
        
        assert "best_models" in insights
        assert "total_observations" in insights
        assert insights["total_observations"] == 5
    
    def test_get_stats(self, optimizer, sample_config, query_class):
        """Test getting optimizer statistics."""
        optimizer.update(query_class, sample_config, 0.7)
        
        stats = optimizer.get_stats()
        
        assert stats["total_posteriors"] >= 1
        assert stats["total_observations"] == 1


# ==============================================================================
# Test Feedback Collector
# ==============================================================================

class TestFeedbackCollector:
    """Tests for FeedbackCollector."""
    
    @pytest.fixture
    def collector(self):
        """Create an in-memory collector."""
        return FeedbackCollector()
    
    def test_get_or_create(self, collector):
        """Test getting or creating feedback."""
        fb1 = collector.get_or_create("conf_123")
        fb2 = collector.get_or_create("conf_123")
        
        assert fb1 is fb2  # Same object
        assert fb1.conference_id == "conf_123"
    
    def test_record_signal(self, collector):
        """Test recording a signal."""
        collector.record_signal("conf_123", "thumbs_up")
        
        fb = collector.get_or_create("conf_123")
        assert len(fb.signals) == 1
        assert fb.signals[0].signal_type == SignalType.THUMBS_UP
    
    def test_record_immediate(self, collector):
        """Test recording immediate feedback."""
        collector.record_immediate("conf_123", useful="yes", will_act="yes")
        
        fb = collector.get_or_create("conf_123")
        assert fb.immediate is not None
        assert fb.immediate.useful == "yes"
    
    def test_record_delayed(self, collector):
        """Test recording delayed feedback."""
        collector.record_delayed("conf_123", outcome="worked", details="Patient improved")
        
        fb = collector.get_or_create("conf_123")
        assert fb.delayed is not None
        assert fb.delayed.outcome == "worked"
    
    def test_get_outcome(self, collector):
        """Test getting outcome score."""
        collector.record_signal("conf_123", "thumbs_up")
        
        outcome = collector.get_outcome("conf_123")
        assert outcome is not None
        assert outcome > 0.5
    
    def test_get_pending_followups(self, collector):
        """Test getting conferences needing follow-up."""
        # Create feedback without delayed
        fb = collector.get_or_create("conf_old")
        fb.created_at = datetime.now() - timedelta(days=15)  # Make it old
        
        pending = collector.get_pending_followups(days_old=14)
        
        assert "conf_old" in pending


# ==============================================================================
# Test Component Effect
# ==============================================================================

class TestComponentEffect:
    """Tests for ComponentEffect model."""
    
    def test_create_effect(self):
        """Test creating component effect."""
        effect = ComponentEffect(
            component_type="agent_model",
            component_value="gpt-4o",
            effect_size=0.85,
            confidence="HIGH",
            sample_size=100,
            std_dev=0.05,
        )
        
        assert effect.effect_size == 0.85
        assert effect.confidence == "HIGH"
    
    def test_effect_no_data(self):
        """Test effect with no data."""
        effect = ComponentEffect(
            component_type="agent_model",
            component_value="unknown",
            confidence="LOW",
            sample_size=0,
        )
        
        assert effect.effect_size is None
        assert effect.confidence == "LOW"

