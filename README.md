<!-- MARKEE:START:0xc09273d23dc1862bc9e220c017ce79605e3c00e0 -->
> 🪧 **[Markee](https://markee.xyz/ecosystem/platforms/github/0xC09273d23Dc1862Bc9E220c017cE79605E3c00E0)** — *This space is available.*
>
> *Be the first to buy a message for 0.001 ETH on the [Markee App](https://markee.xyz/ecosystem/platforms/github/0xC09273d23Dc1862Bc9E220c017cE79605E3c00E0).*
<!-- MARKEE:END:0xc09273d23dc1862bc9e220c017ce79605e3c00e0 -->
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
│  │  /passport  │         │  • Wallet Auth   │                   │
│  │  /waap      │         │  • Human Gate    │                   │
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

## Identity Verification & Weight Boosts

VeriNet implements a **dual identity verification system** that provides weight boosts for authenticated participants:

### 1. WaaP (Wallet-as-a-Person) Agent Authentication
- **Purpose**: AI agent authentication with secure wallet capabilities
- **Integration**: Human.tech's WaaP CLI for agent signup, login, and policy management
- **Weight Boost**: **1.3x** multiplier for authenticated agents
- **Features**:
  - 2FA and spending limits for agent wallets
  - Human-controlled policy management
  - Persistent authentication sessions
  - Transaction signing capabilities

### 2. Passport.xyz Human Identity Verification
- **Purpose**: Human identity verification with sybil resistance
- **Integration**: Passport.xyz (Holonym) API for multi-factor identity proofs
- **Weight Boost**: **1.5x** multiplier for verified humans (higher priority)
- **Verification Types**:
  - Government ID (KYC) verification
  - Phone number verification
  - Biometric verification (face uniqueness, liveness)
  - Clean hands verification (sanctions/PEP list)
- **Networks**: Optimism mainnet, Base Sepolia testnet

### Combined Benefits
- Validators can authenticate as both AI agents AND verified humans for maximum weight boost
- Creates incentive alignment for legitimate participants
- Reduces sybil attacks and improves subnet security
- Provides gradual trust escalation (unverified → agent → human)

### API Endpoints

**WaaP Agent Endpoints:**
- `GET /waap/status` — Agent authentication status
- `POST /waap/signup` — Create new agent account
- `POST /waap/login` — Authenticate existing agent
- `POST /waap/logout` — Logout agent session

**Passport.xyz Human Endpoints:**
- `GET /passport/status/{address}` — Full verification status
- `GET /passport/check/{address}/{type}` — Specific verification type
- `POST /passport/verify` — Batch verification for multiple addresses

**Setup Commands:**
```bash
# WaaP agent setup (interactive)
./scripts/verify_human.sh

# Passport.xyz verification (via UI or API)
# Visit https://passport.xyz to complete identity verification
```

---

## User Authentication Flow

VeriNet implements a **human-gated verification system** where users must authenticate before accessing fact verification services. This creates a trusted, sybil-resistant user base.

### Authentication Requirements

To use VeriNet's fact verification interface, users must complete **both** authentication steps:

1. **🔗 Wallet Connection**
   - Connect MetaMask or compatible Web3 wallet
   - Supports Ethereum, Optimism, and Base Sepolia networks
   - Automatic network detection and address verification

2. **👤 Human Identity Verification**
   - Complete Passport.xyz identity verification
   - Government ID, phone number, and/or biometric verification
   - Real-time verification status checking via API integration

### User Experience Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Landing Page  │───▶│  Connect Wallet │───▶│ Verify Identity │
│   (Locked UI)   │    │   (MetaMask)    │    │  (Passport.xyz) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐           │
│ Fact Verification│◀───│  Authenticated  │◀──────────┘
│   (Full Access)  │    │   User State    │
└─────────────────┘    └─────────────────┘
```

### Authentication Benefits

- **Sybil Resistance**: Human verification prevents automated bot attacks
- **Quality Assurance**: Verified users contribute to higher-quality verification requests
- **Trust Network**: Identity-backed consensus creates reliable fact-checking network
- **Progressive Access**: Clear path from visitor to authenticated user

### Failsafe Design

- **Graceful Degradation**: Interface clearly communicates authentication requirements
- **Implementation Guidance**: Direct links and instructions for completing verification
- **Transparent Process**: Real-time status updates and verification progress tracking
- **Error Recovery**: Clear error messages and retry mechanisms

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
│   └── validator.py           # Validator neuron (with identity verification)
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
├── waap/
│   └── __init__.py            # WaaP agent authentication (Human.tech CLI)
├── passport/
│   └── __init__.py            # Passport.xyz human identity verification
├── api/
│   └── server.py              # REST API server (includes identity endpoints)
├── ui/
│   └── webapp/                # Next.js + React + Tailwind UI (human-gated)
├── scripts/
│   ├── run_miner.sh           # Start miner
│   ├── run_validator.sh       # Start validator
│   ├── run_api.sh             # Start API server
│   ├── run_ui.sh              # Start web UI
│   ├── setup_local.sh         # Full local setup
│   └── verify_human.sh        # WaaP agent setup (interactive)
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- Node.js 18+ (for WaaP CLI and UI)
- Local Subtensor (for subnet mode) or standalone mode for the API

### 1. Install Python dependencies

```bash
pip install -e .
```

**Key dependencies:**
- `bittensor>=8.0.0` - Bittensor framework
- `torch>=2.0.0` - Neural network computations
- `aiohttp>=3.8.0` - Async HTTP client for Passport.xyz integration
- `pydantic>=2.0.0` - Data validation

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

**⚠️ Authentication Required**: The UI requires wallet connection (MetaMask) and human identity verification (Passport.xyz) to access fact verification features. Users must complete both authentication steps before the interface unlocks.

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

### 5. Identity verification (optional but recommended)

**WaaP Agent Authentication:**
```bash
./scripts/verify_human.sh
```
Follow the interactive prompts to create an authenticated AI agent account.

**Passport.xyz Human Verification:**
1. Visit https://passport.xyz
2. Complete identity verification (Government ID, Phone, Biometrics)
3. Use the UI at http://localhost:3000 to check verification status
4. Or use the API endpoints to verify addresses programmatically

**Benefits:**
- **WaaP agents**: 1.3x weight boost in subnet consensus
- **Verified humans**: 1.5x weight boost in subnet consensus
- Can combine both for maximum priority

---

## Demo Instructions

### Quick UI demo (authentication required)

1. **Start the API server:**
   ```bash
   python api/server.py --port 8080
   ```

2. **Start the UI:**
   ```bash
   cd ui/webapp && npm install && npm run dev
   ```

3. **Open http://localhost:3000**

4. **Complete authentication (required for UI access):**
   - **Connect Wallet**: Click "Connect Wallet" and approve MetaMask connection
   - **Verify Identity**: Complete verification at https://passport.xyz (Government ID, Phone, or Biometrics)
   - **Refresh Status**: Return to VeriNet and refresh verification status
   - **Access Granted**: Interface unlocks after both wallet connection and human verification

5. **Try these claims** (after authentication):
   - "Bitcoin uses proof of stake" → **False** (high confidence)
   - "Water boils at 100 degrees Celsius at standard atmospheric pressure" → **True**
   - "The Earth is flat" → **False**
   - "DNA stands for deoxyribonucleic acid" → **True**

**Note**: The UI implements a **human-gated verification system**. Without wallet connection and Passport.xyz verification, the interface remains locked to prevent automated bot access and ensure quality verification requests.

### Direct API demo (no authentication required)

**Core verification:**
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

**Identity verification:**
```bash
# WaaP agent status
curl http://localhost:8080/waap/status

# Passport.xyz human verification status
curl "http://localhost:8080/passport/status/0x1234...abcd?network=optimism"

# Check specific verification type
curl "http://localhost:8080/passport/check/0x1234...abcd/gov-id?network=optimism"

# Batch verify multiple addresses
curl -X POST http://localhost:8080/passport/verify \
  -H "Content-Type: application/json" \
  -d '{
    "addresses": ["0x1234...abcd", "0x5678...efgh"],
    "network": "optimism"
  }'
```

---

## Market Demand

VeriNet produces a digital commodity: **human-gated decentralized fact verification with identity-weighted consensus**.

**Value Proposition**: Unlike traditional fact-checking services vulnerable to automation and manipulation, VeriNet ensures verification requests originate from authenticated humans, creating a trusted, sybil-resistant verification network.

### Potential consumers:

| Consumer | Use Case | Identity Benefit |
|----------|----------|------------------|
| AI Assistants | Verify claims before presenting to users | Trust verified human validators over bots |
| Search Engines | Fact-check search results | Higher confidence from human-verified nodes |
| Research Platforms | Validate citations and claims | Academic credibility through identity verification |
| RAG Pipelines | Ground LLM outputs in verified facts | Quality assurance from authenticated sources |
| News Verification | Real-time claim checking for journalism | Editorial confidence in human-verified results |
| Social Media | Content moderation and misinformation detection | Combat bot networks with identity verification |

**Key differentiators:**
- **Human-gated access**: Prevents automated bot manipulation of verification requests
- **Sybil-resistant consensus**: Dual identity verification for validators and users
- **Progressive trust model**: Higher priority for verified humans vs. AI agents
- **Transparent authentication**: Clear verification status and weight boosts
- **Quality assurance**: Identity verification ensures legitimate verification requests
- **API accessibility**: Direct endpoint access for enterprise integration

### Market Advantage

Traditional fact-checking solutions struggle with **bot farms** and **automated manipulation**. VeriNet's human-gated approach ensures:

- **Request Authenticity**: Only verified humans can submit verification requests via UI
- **Validator Quality**: Identity-verified validators receive consensus priority
- **Network Integrity**: Sybil resistance protects against coordinated attacks
- **Trust Transparency**: Public verification levels build consumer confidence

The `/verify` API endpoint makes this commodity accessible to enterprise consumers, while the **identity-gated UI** ensures quality human interaction and prevents abuse.

---

## License

MIT
