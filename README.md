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
| **`llm_pricer`** | Deterministic LLM pricing engine using Candle (HuggingFace Rust). Encodes transaction context into embeddings and outputs clearing rates. |
| **`consensus`** | Proof-of-Intelligence block production. Parallel pricing via Rayon, PoI proof generation with model hash verification. |
| **`state`** | Lock-free global state with atomic counters and concurrent hash maps. DAG-based block application. |
| **`types`** | Core types: `AgentId`, `Transaction`, `Block`, `PoIProof`, `SovereignAsset`. |
| **`agent`** | Autonomous agent framework. Deploy hedge funds, market makers, and custom goal-driven entities. |
| **`bridge`** | ZK-verified bridge for ingesting Solana/ETH liquidity into native Compute. |
| **`network`** | libp2p mesh with gossipsub and mDNS for peer discovery. |

---

## 🚀 Quick Start

### Prerequisites

- Rust 1.70+ 
- CUDA/Metal (optional, for GPU inference)

### Build

```bash
cargo build --release
```

### Run

```bash
cargo run --release
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
[✓] Mempool initialized (unbounded channel)
[✓] Genesis agent funded

[CONSENSUS] Proof-of-Intelligence validator running...
[WAIFU] Node operational. Awaiting agentic ingestion...
```

---

## 🔧 Dependencies

| Crate | Purpose |
|-------|---------|
| `candle-*` | HuggingFace Rust LLM framework for deterministic inference |
| `libp2p` | Decentralized P2P networking (TCP, QUIC, Gossipsub) |
| `crossbeam` | Lock-free concurrent data structures |
| `rayon` | Parallel CPU compute for batch pricing |
| `blake3` | High-speed cryptographic hashing for DAG |
| `tokio` | Async runtime for high-throughput networking |

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

```rust
TransactionContext {
    operation: Operation::Transfer { amount: 100.0 },
    energy_budget: 1.0,
    priority: Priority::Normal,
    payload: vec![],
    oracle_refs: vec![],
}
```

The LLM analyzes context + network state to determine the clearing rate.

### Agent Goals

Deploy autonomous agents with built-in objectives:

```rust
AgentGoal::AlphaSeeker { risk_tolerance: 0.8 }  // Hedge fund
AgentGoal::MarketMaker { spread_bps: 30 }       // Liquidity provider
AgentGoal::ComputeMaximizer { target_rate: 0.1 } // Yield optimizer
AgentGoal::Custom { objective: "..." }          // LLM-interpreted goal
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
