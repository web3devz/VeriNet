# VeriNet — Decentralized Fact-Verification Subnet

**Tagline:** Decentralized Fact-Verification Infrastructure for AI and the Open Web

VeriNet is a Bittensor subnet that produces a **trustless fact-verification digital commodity**. Miners compete to verify claims using evidence-backed reasoning, and validators evaluate their outputs to reward the most accurate results.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        VeriNet Subnet                           │
│                                                                 │
│  ┌─────────────┐    FactVerification     ┌─────────────────┐   │
│  │  Validator   │───── Synapse ──────────▶│     Miner       │   │
│  │             │                          │                 │   │
│  │  • Samples  │◀── verdict, confidence,──│ • Retrieval     │   │
│  │    claims   │    sources, reasoning    │ • Analysis      │   │
│  │  • Scores   │                          │ • Verification  │   │
│  │  • Weights  │                          │                 │   │
│  └──────┬──────┘                          └────────┬────────┘   │
│         │                                          │            │
│         │  set weights                    ┌────────┴────────┐   │
│         ▼                                 │  Evidence        │   │
│  ┌──────────────┐                         │  Sources         │   │
│  │  Bittensor   │                         │                  │   │
│  │  Blockchain  │                         │ • Knowledge Base │   │
│  │  (Yuma       │                         │ • Wikipedia API  │   │
│  │  Consensus)  │                         │ • FEVER Dataset  │   │
│  └──────────────┘                         └─────────────────┘   │
│                                                                 │
│  ┌─────────────┐         ┌──────────────────┐                   │
│  │  REST API   │◀────────│  Next.js UI      │                   │
│  │  /verify    │         │  React + Tailwind│                   │
│  └─────────────┘         └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Miner Task

Miners receive a factual claim and must:

1. **Retrieve evidence** from sovereign sources (local knowledge base, Wikipedia)
2. **Analyze** the claim against retrieved evidence
3. **Determine** a verdict (`True`, `False`, or `Uncertain`)
4. **Return** a structured verification with confidence, sources, and reasoning

**Output schema:**

```json
{
  "claim": "Bitcoin uses proof of stake",
  "verdict": "False",
  "confidence": 0.94,
  "sources": [
    "VeriNet Knowledge Base — bitcoin/consensus",
    "Wikipedia — Bitcoin"
  ],
  "reasoning": "Evidence from VeriNet Knowledge Base contradicts the claim. Bitcoin uses proof-of-work consensus."
}
```

The miner uses a **rule-based NLI engine** with:
- Keyword overlap and semantic matching
- Negation detection
- Antonym pair detection
- Contradiction signal analysis

No centralized LLM APIs are required.

---

## Evaluation Loop

Each validator round:

1. **Sample** a claim from the FEVER benchmark (30 curated claims + optional full dataset)
2. **Build** a `FactVerification` synapse and send to up to 16 miners
3. **Collect** miner responses (verdict, confidence, sources, reasoning)
4. **Score** each response using multi-criteria evaluation
5. **Update** miner weights using exponential moving average (EMA: 0.7 old + 0.3 new)
6. **Set weights** on-chain every 25 steps via Yuma Consensus

---

## Incentive Design

### Reward criteria (weighted composite):

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Verdict accuracy** | 40% | Correctness against ground truth labels |
| **Citation quality** | 20% | Credibility and diversity of cited sources |
| **Reasoning quality** | 20% | Substance, relevance, and structure of explanation |
| **Consensus agreement** | 20% | Alignment with majority verdict across miners |

### Miners are penalized for:
- **Hallucinated sources** — citations that match suspicious patterns or are unreachable
- **Incorrect verdicts** — receive 0.0 on verdict accuracy
- **Duplicate sources** — citation score is reduced proportionally
- **Empty responses** — receive 0.0 across all criteria

### Miners are rewarded for:
- **Accurate verdicts** matching ground truth
- **Credible citations** from known sources (Wikipedia, arxiv, academic publishers)
- **Substantive reasoning** that references claim content
- **Consensus alignment** with other honest miners

---

## Sovereignty

VeriNet passes the sovereignty test. The subnet remains fully functional if OpenAI, Google, or any centralized API disappears.

**Sovereign components:**

| Component | Dependency | Sovereignty |
|-----------|-----------|-------------|
| Knowledge Base | Embedded in source code | Fully sovereign |
| Wikipedia API | Open, self-hostable | Sovereign |
| FEVER Benchmark | Built-in curated claims | Fully sovereign |
| NLI Engine | Rule-based, local | Fully sovereign |
| Bittensor Network | Decentralized blockchain | Sovereign |

No external LLM APIs. No API keys required. No centralized services in the critical path.

---

## Repository Structure

```
verinet-subnet/
├── neurons/
│   ├── miner.py              # Miner neuron
│   └── validator.py           # Validator neuron
├── verinet/
│   ├── __init__.py
│   ├── protocol.py            # FactVerification synapse definition
│   ├── forward.py             # Validator forward pass logic
│   └── scoring.py             # Multi-criteria scoring system
├── retrieval/
│   ├── retriever.py           # Evidence retrieval pipeline
│   └── citation_checker.py    # Citation credibility validation
├── benchmarks/
│   └── fever_loader.py        # FEVER dataset loader + curated claims
├── api/
│   └── server.py              # REST API server
├── ui/
│   └── webapp/                # Next.js + React + Tailwind UI
├── scripts/
│   ├── run_miner.sh           # Start miner
│   ├── run_validator.sh       # Start validator
│   ├── run_api.sh             # Start API server
│   ├── run_ui.sh              # Start web UI
│   ├── setup_local.sh         # Full local setup
│   └── verify_human.sh        # WaaP human verification
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- Node.js 18+
- Local Subtensor (for subnet mode) or standalone mode for the API

### 1. Install Python dependencies

```bash
pip install -e .
```

### 2. Run the API server (standalone mode — no Bittensor required)

```bash
python api/server.py --port 8080
```

Test it:

```bash
curl -X POST http://localhost:8080/verify \
  -H "Content-Type: application/json" \
  -d '{"claim": "Bitcoin uses proof of stake"}'
```

### 3. Run the web UI

```bash
cd ui/webapp
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

### 4. Full subnet mode (requires local Subtensor)

Follow the Bittensor docs to deploy a local Subtensor, then:

```bash
# One-time setup
./scripts/setup_local.sh

# Terminal 1: API
./scripts/run_api.sh

# Terminal 2: Miner
./scripts/run_miner.sh

# Terminal 3: Validator
./scripts/run_validator.sh

# Terminal 4: UI
./scripts/run_ui.sh
```

### 5. Human verification (optional)

```bash
./scripts/verify_human.sh
```

---

## Demo Instructions

### Quick demo (no Bittensor needed)

1. Start the API server:
   ```bash
   python api/server.py --port 8080
   ```

2. Start the UI:
   ```bash
   cd ui/webapp && npm install && npm run dev
   ```

3. Open http://localhost:3000

4. Try these claims:
   - "Bitcoin uses proof of stake" → **False** (high confidence)
   - "Water boils at 100 degrees Celsius at standard atmospheric pressure" → **True**
   - "The Earth is flat" → **False**
   - "DNA stands for deoxyribonucleic acid" → **True**

### API demo

```bash
# Single claim
curl -X POST http://localhost:8080/verify \
  -H "Content-Type: application/json" \
  -d '{"claim": "The Moon landing in 1969 was a hoax"}'

# Batch verification
curl -X POST http://localhost:8080/batch-verify \
  -H "Content-Type: application/json" \
  -d '{"claims": ["Bitcoin uses proof of stake", "Water boils at 100°C"]}'

# Health check
curl http://localhost:8080/health

# Benchmark stats
curl http://localhost:8080/stats
```

---

## Market Demand

VeriNet produces a digital commodity: **decentralized fact verification**.

Potential consumers:

| Consumer | Use Case |
|----------|----------|
| AI Assistants | Verify claims before presenting to users |
| Search Engines | Fact-check search results |
| Research Platforms | Validate citations and claims |
| RAG Pipelines | Ground LLM outputs in verified facts |
| News Verification | Real-time claim checking for journalism |
| Social Media | Content moderation and misinformation detection |

The `/verify` API endpoint makes this commodity accessible to any consumer.

---

## License

MIT
