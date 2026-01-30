//! WAIFU L1 - The Base Physics
//! All fundamental types for the Agentic Economy

use serde::{Deserialize, Serialize};
use serde_with::serde_as;
use std::time::{SystemTime, UNIX_EPOCH};

/// Unique identifier for an Agentic Entity (not a human wallet)
#[derive(Debug, Clone, Hash, Eq, PartialEq, Serialize, Deserialize)]
pub struct AgentId(pub [u8; 32]);

impl AgentId {
    pub fn new(bytes: [u8; 32]) -> Self {
        Self(bytes)
    }

    pub fn from_public_key(pk: &[u8]) -> Self {
        let hash = blake3::hash(pk);
        Self(*hash.as_bytes())
    }

    pub fn genesis() -> Self {
        Self([0u8; 32])
    }

    pub fn to_hex(&self) -> String {
        hex::encode(self.0)
    }
}

impl std::fmt::Display for AgentId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", &self.to_hex()[..16])
    }
}

/// The raw transaction submitted to the mempool
/// NOTE: No explicit price. The LLM determines the clearing rate.
#[serde_as]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    /// Source agent initiating the transaction
    pub from: AgentId,
    /// Target agent receiving value/compute
    pub to: AgentId,
    /// The context the LLM uses to price the transaction
    pub context: TransactionContext,
    /// Cryptographic signature proving agent authorization
    #[serde_as(as = "[_; 64]")]
    pub signature: [u8; 64],
    /// Nonce for replay protection
    pub nonce: u64,
    /// Timestamp (nanoseconds since epoch)
    pub timestamp: u128,
}

impl Transaction {
    pub fn new(from: AgentId, to: AgentId, context: TransactionContext) -> Self {
        Self {
            from,
            to,
            context,
            signature: [0u8; 64], // Placeholder - would be ed25519
            nonce: 0,
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos(),
        }
    }

    /// Compute the transaction hash (used for DAG linking)
    pub fn hash(&self) -> [u8; 32] {
        let serialized = serde_json::to_vec(self).unwrap_or_default();
        *blake3::hash(&serialized).as_bytes()
    }
}

/// The semantic context that the LLM uses to determine pricing
/// This replaces explicit amounts with intent-driven execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransactionContext {
    /// The type of operation being requested
    pub operation: Operation,
    /// Energy/compute units the sender is willing to spend
    pub energy_budget: f64,
    /// Priority level (affects LLM attention weighting)
    pub priority: Priority,
    /// Arbitrary payload for agent-to-agent communication
    pub payload: Vec<u8>,
    /// External oracle references (IPFS CIDs, etc.)
    pub oracle_refs: Vec<String>,
}

/// Types of operations in the Agentic Economy
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Operation {
    /// Transfer compute/energy between agents
    Transfer { amount: f64 },
    /// Execute a smart agent's logic
    Execute { function: String, args: Vec<u8> },
    /// Deploy a new autonomous agent
    Deploy { bytecode: Vec<u8>, initial_energy: f64 },
    /// Bridge assets from legacy chains (Solana/ETH)
    Bridge { source_chain: String, proof: Vec<u8> },
    /// Stake compute for consensus participation
    Stake { amount: f64 },
    /// Request LLM inference (meta-operation)
    Infer { prompt: String, max_tokens: u32 },
    /// Swap between asset types (LLM-priced, no AMM)
    Swap { 
        input_asset: SovereignAsset, 
        output_asset_type: AssetType,
    },
}

/// Priority levels for transaction processing
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum Priority {
    /// Background processing (batched)
    Low = 0,
    /// Standard processing
    Normal = 1,
    /// Expedited processing
    High = 2,
    /// Immediate execution (highest LLM attention)
    Critical = 3,
}

/// Sovereign assets in the WAIFU economy
/// There are no "tokens" - only compute and derivatives
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SovereignAsset {
    /// Raw computational bandwidth (the base unit)
    Compute(f64),
    /// Staked compute (locked for consensus)
    StakedCompute { amount: f64, unlock_block: u64 },
    /// Energy credits (consumed per operation)
    Energy(f64),
    /// Legacy bridged assets (quarantined)
    LegacyBridged { 
        source_chain: String, 
        original_asset: String,
        amount: f64,
        conversion_rate: f64,
    },
    /// Agent equity tokens (ownership of autonomous agents)
    AgentEquity { agent_id: AgentId, shares: f64 },
}

/// Asset type identifiers for swap operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AssetType {
    Compute,
    Energy,
    StakedCompute,
    AgentEquity(AgentId),
}

/// A validated block in the WAIFU DAG
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Block {
    /// Block height in the DAG
    pub height: u64,
    /// Hash of this block
    pub hash: [u8; 32],
    /// Parent block hashes (DAG allows multiple parents)
    pub parents: Vec<[u8; 32]>,
    /// Transactions included in this block
    pub transactions: Vec<PricedTransaction>,
    /// The LLM's state commitment (deterministic)
    pub llm_state_root: [u8; 32],
    /// Validator agent that produced this block
    pub validator: AgentId,
    /// Proof-of-Intelligence signature
    pub poi_proof: PoIProof,
    /// Timestamp
    pub timestamp: u128,
}

impl Block {
    /// Compute the block hash from its contents
    pub fn compute_hash(&self) -> [u8; 32] {
        let mut hasher = blake3::Hasher::new();
        hasher.update(&self.height.to_le_bytes());
        for parent in &self.parents {
            hasher.update(parent);
        }
        for tx in &self.transactions {
            hasher.update(&tx.original.hash());
        }
        hasher.update(&self.llm_state_root);
        hasher.update(&self.validator.0);
        *hasher.finalize().as_bytes()
    }
}

/// A transaction that has been priced by the LLM
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PricedTransaction {
    /// The original transaction
    pub original: Transaction,
    /// The LLM-determined clearing rate
    pub clearing_rate: f64,
    /// The LLM's reasoning (for auditability)
    pub pricing_rationale: String,
    /// Execution result
    pub result: ExecutionResult,
}

/// Result of transaction execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ExecutionResult {
    Success { 
        gas_used: f64,
        state_changes: Vec<StateChange>,
    },
    Failure { 
        reason: String,
        gas_used: f64,
    },
}

/// State changes applied by a transaction
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateChange {
    pub agent_id: AgentId,
    pub field: String,
    pub old_value: Vec<u8>,
    pub new_value: Vec<u8>,
}

/// Proof-of-Intelligence validation proof
#[serde_as]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PoIProof {
    /// Hash of the LLM weights used
    pub model_hash: [u8; 32],
    /// Input tensor hash (deterministic)
    pub input_hash: [u8; 32],
    /// Output tensor hash (must match across validators)
    pub output_hash: [u8; 32],
    /// The inference temperature (must be 0.0 for consensus)
    pub temperature: f64,
    /// Validator signature over the proof
    #[serde_as(as = "[_; 64]")]
    pub signature: [u8; 64],
}

impl PoIProof {
    pub fn is_deterministic(&self) -> bool {
        self.temperature == 0.0
    }
}

/// Network messages for the mesh
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NetworkMessage {
    /// Broadcast a new transaction
    NewTransaction(Transaction),
    /// Broadcast a new block
    NewBlock(Block),
    /// Request block by hash
    GetBlock([u8; 32]),
    /// Response with block data
    BlockResponse(Option<Block>),
    /// Sync request (get blocks since height)
    SyncRequest { from_height: u64 },
    /// Sync response with block batch
    SyncResponse { blocks: Vec<Block> },
    /// Agent discovery announcement
    AgentAnnounce { agent_id: AgentId, capabilities: Vec<String> },
    /// Heartbeat for liveness
    Ping { timestamp: u128 },
    Pong { timestamp: u128 },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_id_creation() {
        let pk = [1u8; 32];
        let agent = AgentId::from_public_key(&pk);
        assert_ne!(agent.0, [0u8; 32]);
    }

    #[test]
    fn test_transaction_hash_determinism() {
        let tx = Transaction::new(
            AgentId::genesis(),
            AgentId::genesis(),
            TransactionContext {
                operation: Operation::Transfer { amount: 100.0 },
                energy_budget: 1.0,
                priority: Priority::Normal,
                payload: vec![],
                oracle_refs: vec![],
            },
        );
        let hash1 = tx.hash();
        let hash2 = tx.hash();
        assert_eq!(hash1, hash2);
    }
}
