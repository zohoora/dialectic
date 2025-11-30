# AI Case Conference System

A multi-agent deliberation system for complex clinical decision support. Multiple AI agents with different epistemic roles (Advocate, Skeptic, Empiricist) debate clinical questions over multiple rounds, then an Arbitrator synthesizes the discussion into actionable recommendations.

## Features

- **Multi-Agent Deliberation**: 3 agents with distinct roles debate clinical questions
- **Multiple Rounds**: Agents see each other's responses and can critique/refine positions
- **Arbitrator Synthesis**: Final synthesis with confidence levels and preserved dissent
- **Cost Tracking**: Token usage and cost estimation per conference
- **Web UI**: Streamlit-based interface for easy interaction
- **Flexible Configuration**: Choose models, number of rounds, and agent roles

## Quick Start

### 1. Install Dependencies

```bash
cd dialectic
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up API Key

Copy the environment template and add your OpenRouter API key:

```bash
cp env.template .env
# Edit .env and add your OPENROUTER_API_KEY
```

Get an API key from [OpenRouter](https://openrouter.ai/).

### 3. Run the Web UI

```bash
streamlit run ui/app.py
```

Open http://localhost:8501 in your browser.

### 4. Run Tests

```bash
# Run all unit tests
pytest tests/ -v

# Run integration tests (requires API key)
RUN_INTEGRATION_TESTS=1 pytest tests/test_integration.py -v
```

## Architecture

```
dialectic/
├── src/
│   ├── models/          # Pydantic data models
│   ├── llm/             # LLM client (OpenRouter)
│   ├── conference/      # Conference engine, agents, arbitrator
│   └── utils/           # Prompts, logging, utilities
├── prompts/
│   └── agents/          # Role-specific prompts
├── config/              # Model and role configurations
├── ui/                  # Streamlit web application
└── tests/               # Unit and integration tests
```

## Agent Roles

| Role | Purpose |
|------|---------|
| **Advocate** | Builds the strongest case for the most promising approach |
| **Skeptic** | Challenges emerging consensus, identifies risks |
| **Empiricist** | Grounds discussion in clinical trial evidence |
| **Arbitrator** | Synthesizes discussion into actionable consensus |

## Configuration

Edit `config/models.yaml` to configure model pricing and defaults.
Edit `config/roles.yaml` to customize agent behaviors.

## Programmatic Usage

```python
import asyncio
from src.conference.engine import ConferenceEngine, create_default_config
from src.llm.client import LLMClient

async def run_conference():
    client = LLMClient()  # Uses OPENROUTER_API_KEY from environment
    engine = ConferenceEngine(client)
    
    config = create_default_config(
        advocate_model="anthropic/claude-3.5-sonnet",
        skeptic_model="openai/gpt-4o",
        empiricist_model="google/gemini-pro-1.5",
        arbitrator_model="anthropic/claude-3.5-sonnet",
        num_rounds=2,
    )
    
    result = await engine.run_conference(
        query="What is the best treatment for condition X?",
        config=config,
    )
    
    print(f"Synthesis: {result.synthesis.final_consensus}")
    print(f"Cost: ${result.token_usage.estimated_cost_usd:.4f}")

asyncio.run(run_conference())
```

## Future Phases

This is Phase 1 of a larger system. Future phases will add:

- **Phase 2**: Grounding Layer (PubMed citation verification)
- **Phase 3**: Fragility Testing (perturbation stress tests)
- **Phase 4**: Experience Library (heuristic storage/retrieval)
- **Phase 5**: Gatekeeper + Surgeon (extraction pipeline)
- **Phase 6**: Learning Loop (contextual bandit optimization)

## License

MIT License - See LICENSE file for details.

