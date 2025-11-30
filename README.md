# AI Case Conference System

A multi-agent deliberation system for complex clinical decision support. Multiple AI agents with different epistemic roles (Advocate, Skeptic, Empiricist, Mechanist, Patient Voice) debate clinical questions over multiple rounds, then an Arbitrator synthesizes the discussion into actionable recommendations.

## Features

- **Multi-Agent Deliberation**: Up to 5 agents with distinct epistemic roles
- **Conference Topologies**: Free Discussion, Oxford Debate, Delphi Method, Socratic Spiral, Red Team/Blue Team
- **Citation Grounding**: Automatic PubMed verification of cited studies
- **Fragility Testing**: Stress-test recommendations against clinical variations
- **Experience Library**: Store and retrieve generalizable heuristics
- **Self-Optimization**: Thompson Sampling with feedback loop
- **Shadow Mode**: Counterfactual testing of alternative configurations
- **Cost Tracking**: Token usage and cost estimation per conference
- **Web UI**: Streamlit-based interface with real-time progress

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

## Deployment to Streamlit Cloud

Deploy with zero DevOps using [Streamlit Community Cloud](https://streamlit.io/cloud):

### 1. Push to GitHub

Ensure your repository is on GitHub (public or private).

### 2. Connect to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your repository
5. Set main file path: `ui/app.py`
6. Click **"Deploy"**

### 3. Configure Secrets

In the Streamlit Cloud dashboard:

1. Click your app's **Settings** (gear icon)
2. Go to **"Secrets"** section
3. Add your API key:

```toml
OPENROUTER_API_KEY = "sk-or-your-key-here"
```

Your app will be live at `https://your-app-name.streamlit.app`

## Running Tests

```bash
# Run all unit tests
pytest tests/ -v

# Run integration tests (requires API key)
RUN_INTEGRATION_TESTS=1 pytest tests/test_integration.py -v

# Run specific test modules
pytest tests/test_topologies.py -v
pytest tests/test_grounding_integration.py -v
```

## Architecture

```
dialectic/
├── src/
│   ├── models/          # Pydantic data models
│   ├── llm/             # LLM client (OpenRouter) with cost tracking
│   ├── conference/      # Conference engine, agents, arbitrator
│   │   └── topologies/  # Deliberation patterns (Oxford, Delphi, etc.)
│   ├── grounding/       # PubMed citation verification
│   ├── fragility/       # Perturbation stress testing
│   ├── learning/        # Experience library, classifier, optimizer
│   ├── shadow/          # Counterfactual configuration testing
│   └── utils/           # Prompts, logging, utilities
├── prompts/             # LLM prompt templates
│   ├── agents/          # Role-specific prompts
│   ├── fragility/       # Stress test prompts
│   ├── learning/        # Extraction prompts
│   └── shadow/          # Judge prompts
├── config/              # Model, role, and topology configurations
├── ui/                  # Streamlit web application
├── data/                # Runtime data (experience library, optimizer state)
└── tests/               # Unit and integration tests
```

## Agent Roles

| Role | Purpose |
|------|---------|
| **Advocate** | Builds the strongest case for the most promising approach |
| **Skeptic** | Challenges emerging consensus, identifies risks and flaws |
| **Empiricist** | Grounds discussion in clinical trial evidence |
| **Mechanist** | Evaluates biological plausibility and mechanisms |
| **Patient Voice** | Represents patient perspective on tolerability and QoL |
| **Arbitrator** | Synthesizes discussion into actionable consensus |

## Conference Topologies

| Topology | Best For |
|----------|----------|
| **Free Discussion** | Exploratory questions, broad clinical scenarios |
| **Oxford Debate** | Binary decisions (treatment A vs B) |
| **Delphi Method** | Reducing anchoring bias, anonymous deliberation |
| **Socratic Spiral** | Complex diagnostics, surfacing assumptions |
| **Red Team / Blue Team** | Risk assessment, adversarial review |

## Configuration

Edit `config/models.yaml` to configure model pricing and defaults.
Edit `config/roles.yaml` to customize agent behaviors.

## Programmatic Usage

```python
import asyncio
from src.conference.engine import ConferenceEngine, create_default_config
from src.llm.client import LLMClient
from src.grounding.engine import GroundingEngine

async def run_conference():
    client = LLMClient()  # Uses OPENROUTER_API_KEY from environment
    grounding_engine = GroundingEngine()  # For citation verification
    engine = ConferenceEngine(client, grounding_engine=grounding_engine)
    
    # Configure with specific agents
    config = create_default_config(
        active_agents={
            "advocate": "openai/gpt-5.1",
            "skeptic": "deepseek/deepseek-r1",
            "empiricist": "google/gemini-3-pro-preview",
        },
        arbitrator_model="anthropic/claude-opus-4.5",
        num_rounds=2,
        topology="free_discussion",  # or oxford_debate, delphi_method, etc.
    )
    
    result = await engine.run_conference(
        query="What is the best treatment for condition X?",
        config=config,
        enable_grounding=True,
        enable_fragility=True,
        fragility_tests=3,
    )
    
    print(f"Synthesis: {result.synthesis.final_consensus}")
    print(f"Confidence: {result.synthesis.confidence:.0%}")
    print(f"Cost: ${result.token_usage.estimated_cost_usd:.4f}")
    
    if result.grounding_report:
        print(f"Citations verified: {len(result.grounding_report.citations_verified)}")
    
    if result.fragility_report:
        print(f"Fragility: {result.fragility_report.fragility_level}")

asyncio.run(run_conference())
```

## System Components

| Component | Description |
|-----------|-------------|
| **Conference Engine** | Orchestrates multi-agent deliberation |
| **Grounding Layer** | Verifies citations against PubMed |
| **Fragility Tester** | Stress-tests recommendations |
| **Experience Library** | Stores/retrieves generalizable heuristics |
| **Gatekeeper** | Evaluates conference quality for extraction |
| **Surgeon** | Extracts heuristics from high-quality conferences |
| **Query Classifier** | Categorizes queries by type, domain, complexity |
| **Configuration Optimizer** | Thompson Sampling for model selection |
| **Shadow Runner** | Counterfactual testing of configurations |

## License

MIT License - See LICENSE file for details.

