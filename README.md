<p align="center">
  <h1 align="center">Waifu Layer</h1>
  <p align="center"><strong>The Agentic Layer 1 Blockchain</strong></p>
</p>

<p align="center">
  <a href="#features"><img src="https://img.shields.io/badge/🧠-LLM_Powered-blueviolet?style=for-the-badge" alt="LLM Powered"></a>
  <a href="#features"><img src="https://img.shields.io/badge/⚡-Lock_Free-00d4aa?style=for-the-badge" alt="Lock Free"></a>
  <a href="#features"><img src="https://img.shields.io/badge/🤖-Autonomous_Agents-ff6b6b?style=for-the-badge" alt="Autonomous Agents"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT0-blue?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <strong>WAIFU</strong> is a next-generation Layer 1 blockchain where <em>LLMs replace AMMs</em>, <em>agents replace corporations</em>, and <em>intelligence is the consensus mechanism</em>.
</p>

---

## 🌟 Features

<table>
<tr>
<td width="50%">

### 🧠 Proof-of-Intelligence Consensus
Traditional blockchains waste energy on meaningless hashes. WAIFU validators run **deterministic LLM inference** (temperature=0) to price transactions and produce blocks.

</td>
<td width="50%">

### ⚡ Lock-Free DAG State
No EVM bottlenecks. Parallel state access via **DAG reconciliation** with crossbeam lock-free data structures. 100k+ transactions per block.

</td>
</tr>
<tr>
<td width="50%">

### 🤖 Autonomous Agents
Smart contracts that are **living AI entities**. Deploy hedge funds, market makers, and infrastructure providers that operate autonomously with equity and revenue distribution.

</td>
<td width="50%">

### 🌉 Sovereign Bridge
Trustless ZK-bridge to ingest liquidity from Solana, Ethereum, and legacy chains. LLM-assessed conversion to native Compute units.

</td>
</tr>
<tr>
<td width="50%">

### 💰 LLM Pricing Engine
**No order books. No AMMs.** A deterministic LLM analyzes transaction context, network state, and agent reputation to set clearing rates in real-time.

</td>
<td width="50%">

### 🌐 Mesh Network
libp2p + QUIC networking with gossipsub for unblockable agent-to-agent streaming. Decentralized by design.

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WAIFU L1 NODE                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  LLM Pricer │  │  Consensus  │  │     Agentic State       │  │
│  │  (Candle)   │→ │    (PoI)    │→ │   (Lock-Free DAG)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│         ↑               ↑                      ↑                │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     Transaction Mempool                      ││
│  │               (unbounded async channel)                      ││
│  └─────────────────────────────────────────────────────────────┘│
│         ↑               ↑                      ↑                │
│  ┌───────────┐  ┌───────────────┐  ┌──────────────────────────┐ │
│  │  Agents   │  │    Bridge     │  │   P2P Network (libp2p)   │ │
│  │ (Deploy)  │  │ (ZK Ingest)   │  │   QUIC + Gossipsub       │ │
│  └───────────┘  └───────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Modules

| Module | Description |
|--------|-------------|
| **`llm_pricer`** | Deterministic LLM pricing engine using numpy for the underlying tensor math (a faithful substitute for Candle here, since neither ever performs real model inference -- see the module docstring). Encodes transaction context into embeddings and outputs clearing rates. |
| **`consensus`** | Proof-of-Intelligence block production. Parallel pricing via a thread pool, PoI proof generation with model hash verification. |
| **`state`** | Global state guarded by `threading` locks (Python has no lock-free atomics/concurrent maps). DAG-based block application. |
| **`types`** | Core types: `AgentId`, `Transaction`, `Block`, `PoIProof`, `SovereignAsset`. |
| **`agent`** | Autonomous agent framework. Deploy hedge funds, market makers, and custom goal-driven entities. |
| **`bridge`** | ZK-"verified" (a hash-based stand-in, not real Groth16/PLONK) bridge for ingesting Solana/ETH liquidity into native Compute. |
| **`network`** | Peer/PeerId bookkeeping stand-in; unwired and inert, same as the original (no libp2p transport was ever wired into `main`). |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+

### Install

```bash
pip install -e .
```

### Run

```bash
python -m waifu_layer.main
```

You'll see:

```
╦ ╦╔═╗╦╔═╗╦ ╦  ╦  ╔╦╗
║║║╠═╣║╠╣ ║ ║  ║   ║ 
╚╩╝╩ ╩╩╚  ╚═╝  ╩═╝ ╩ 
The Agentic Layer 1 - v1.0.0

STATUS: AGENTIC SINGULARITY ONLINE

[✓] Global state initialized (lock-free DAG)
[✓] LLM Pricer loaded (deterministic mode)
[✓] Mempool initialized (unbounded queue)
[✓] Genesis agent funded

[CONSENSUS] Proof-of-Intelligence validator running...
[WAIFU] Node operational. Awaiting agentic ingestion...
```

---

## 🔧 Dependencies

| Package | Purpose |
|---------|---------|
| `numpy` | Tensor math for the pricing engine's matmuls |
| `blake3` | High-speed cryptographic hashing for DAG |
| `asyncio` (stdlib) | Async runtime for the node's mempool/validator loop |
| `threading` (stdlib) | Locking for the concurrent global state |
| `concurrent.futures` (stdlib) | Thread pool for batch transaction pricing |

---

## 💡 Core Concepts

### Sovereign Assets

WAIFU has no "tokens" in the traditional sense. The economy runs on:

- **Compute** — Raw computational bandwidth, the base unit
- **Energy** — Consumed per operation
- **Staked Compute** — Locked for consensus participation
- **Agent Equity** — Shares in autonomous agents

### Transaction Pricing

Transactions don't specify gas prices. Instead, they submit **context**:

```python
TransactionContext(
    operation=Operation.transfer(100.0),
    energy_budget=1.0,
    priority=Priority.NORMAL,
    payload=b"",
    oracle_refs=[],
)
```

The LLM analyzes context + network state to determine the clearing rate.

### Agent Goals

Deploy autonomous agents with built-in objectives:

```python
AgentGoal.alpha_seeker(0.8)          # Hedge fund
AgentGoal.market_maker(30)           # Liquidity provider
AgentGoal.compute_maximizer(0.1)     # Yield optimizer
AgentGoal.custom("...")              # LLM-interpreted goal
```

---

## 📄 License

MIT No Attribution — See [LICENSE](LICENSE)

---

<p align="center">
  <strong>⚠️ EXPERIMENTAL SOFTWARE ⚠️</strong><br>
  <sub>This is a research prototype. Do not use in production.</sub>
</p>

<p align="center">
  <sub>Built with 🧠 by <a href="https://github.com/WaifuAI">WaifuAI</a></sub>
</p>
