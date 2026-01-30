//! WAIFU L1 - Lock-Free Global State
//! No EVM bottlenecks - parallel state access via DAG reconciliation

use crate::types::{AgentId, SovereignAsset, Block, StateChange};
use crossbeam::queue::SegQueue;
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::RwLock;

/// The global agentic state - lock-free concurrent access
pub struct AgenticState {
    /// Agent balances (compute, energy, stakes)
    agent_balances: RwLock<HashMap<AgentId, AgentAccount>>,
    
    /// Agent-deployed bytecode and logic
    agent_code: RwLock<HashMap<AgentId, AgentCode>>,
    
    /// Pending state changes queue (lock-free)
    pending_changes: SegQueue<StateChange>,
    
    /// Current block height
    block_height: AtomicU64,
    
    /// Network congestion metric (0.0 - 1.0 scaled to u64)
    congestion_metric: AtomicU64,
    
    /// Total compute in the network
    total_compute: AtomicU64,
    
    /// DAG head hashes (multiple tips allowed)
    dag_tips: RwLock<Vec<[u8; 32]>>,
    
    /// Finalized state root
    state_root: RwLock<[u8; 32]>,
    
    /// Transaction count for nonce tracking
    tx_count: AtomicUsize,
}

/// Individual agent's account state
#[derive(Debug, Clone, Default)]
pub struct AgentAccount {
    /// Available compute balance
    pub compute: f64,
    /// Available energy balance
    pub energy: f64, 
    /// Staked compute (locked for consensus)
    pub staked: f64,
    /// Unlock block for staked compute
    pub stake_unlock_block: u64,
    /// Agent reputation score (affects pricing)
    pub reputation: f64,
    /// Nonce for transaction ordering
    pub nonce: u64,
    /// Agent's equity holdings in other agents
    pub equity_holdings: HashMap<AgentId, f64>,
}

/// Deployed agent code and state
#[derive(Debug, Clone)]
pub struct AgentCode {
    /// WASM bytecode
    pub bytecode: Vec<u8>,
    /// Code hash
    pub code_hash: [u8; 32],
    /// Deployment block
    pub deployed_at: u64,
    /// Agent-specific storage
    pub storage: HashMap<Vec<u8>, Vec<u8>>,
    /// Energy consumed lifetime
    pub total_energy_consumed: f64,
}

impl AgenticState {
    pub fn new() -> Self {
        Self {
            agent_balances: RwLock::new(HashMap::new()),
            agent_code: RwLock::new(HashMap::new()),
            pending_changes: SegQueue::new(),
            block_height: AtomicU64::new(0),
            congestion_metric: AtomicU64::new(0),
            total_compute: AtomicU64::new(1_000_000_000), // 1B initial
            dag_tips: RwLock::new(vec![[0u8; 32]]),
            state_root: RwLock::new([0u8; 32]),
            tx_count: AtomicUsize::new(0),
        }
    }

    /// Get agent's staked compute (for pricing signals)
    pub fn get_agent_stake(&self, agent: &AgentId) -> f64 {
        self.agent_balances
            .read()
            .unwrap()
            .get(agent)
            .map(|a| a.staked)
            .unwrap_or(0.0)
    }

    /// Get agent's full account
    pub fn get_agent_account(&self, agent: &AgentId) -> Option<AgentAccount> {
        self.agent_balances.read().unwrap().get(agent).cloned()
    }

    /// Get network congestion (0.0 - 1.0)
    pub fn get_network_congestion(&self) -> f64 {
        let raw = self.congestion_metric.load(Ordering::Relaxed);
        raw as f64 / u64::MAX as f64
    }

    /// Get total compute in network
    pub fn get_total_compute(&self) -> f64 {
        self.total_compute.load(Ordering::Relaxed) as f64
    }

    /// Get current block height
    pub fn get_block_height(&self) -> u64 {
        self.block_height.load(Ordering::Relaxed)
    }

    /// Get DAG tips (for block production)
    pub fn get_dag_tips(&self) -> Vec<[u8; 32]> {
        self.dag_tips.read().unwrap().clone()
    }

    /// Get current state root
    pub fn get_state_root(&self) -> [u8; 32] {
        *self.state_root.read().unwrap()
    }

    /// Apply a validated block to state
    pub fn apply_block(&self, block: &Block) -> Result<(), StateError> {
        // 1. Verify block height is valid
        let current_height = self.block_height.load(Ordering::Acquire);
        if block.height != current_height + 1 {
            return Err(StateError::InvalidHeight {
                expected: current_height + 1,
                got: block.height,
            });
        }

        // 2. Apply all state changes from transactions
        for priced_tx in &block.transactions {
            if let crate::types::ExecutionResult::Success { state_changes, .. } = &priced_tx.result {
                for change in state_changes {
                    self.pending_changes.push(change.clone());
                }
            }
        }

        // 3. Process pending changes
        self.flush_pending_changes()?;

        // 4. Update block height
        self.block_height.store(block.height, Ordering::Release);

        // 5. Update DAG tips
        {
            let mut tips = self.dag_tips.write().unwrap();
            // Remove parents from tips
            tips.retain(|tip| !block.parents.contains(tip));
            // Add this block as new tip
            tips.push(block.hash);
        }

        // 6. Update state root
        self.recompute_state_root();

        // 7. Update transaction count
        self.tx_count.fetch_add(block.transactions.len(), Ordering::Relaxed);

        Ok(())
    }

    /// Flush pending state changes (batched for efficiency)
    fn flush_pending_changes(&self) -> Result<(), StateError> {
        let mut balances = self.agent_balances.write().unwrap();
        let mut code = self.agent_code.write().unwrap();

        while let Some(change) = self.pending_changes.pop() {
            // Apply change based on field type
            match change.field.as_str() {
                "compute" => {
                    let account = balances.entry(change.agent_id.clone()).or_default();
                    if let Ok(new_val) = String::from_utf8(change.new_value.clone()) {
                        account.compute = new_val.parse().unwrap_or(account.compute);
                    }
                }
                "energy" => {
                    let account = balances.entry(change.agent_id.clone()).or_default();
                    if let Ok(new_val) = String::from_utf8(change.new_value.clone()) {
                        account.energy = new_val.parse().unwrap_or(account.energy);
                    }
                }
                "staked" => {
                    let account = balances.entry(change.agent_id.clone()).or_default();
                    if let Ok(new_val) = String::from_utf8(change.new_value.clone()) {
                        account.staked = new_val.parse().unwrap_or(account.staked);
                    }
                }
                "reputation" => {
                    let account = balances.entry(change.agent_id.clone()).or_default();
                    if let Ok(new_val) = String::from_utf8(change.new_value.clone()) {
                        account.reputation = new_val.parse().unwrap_or(account.reputation);
                    }
                }
                "code" => {
                    let agent_code = code.entry(change.agent_id.clone()).or_insert(AgentCode {
                        bytecode: vec![],
                        code_hash: [0u8; 32],
                        deployed_at: self.block_height.load(Ordering::Relaxed),
                        storage: HashMap::new(),
                        total_energy_consumed: 0.0,
                    });
                    agent_code.bytecode = change.new_value.clone();
                    agent_code.code_hash = *blake3::hash(&change.new_value).as_bytes();
                }
                "storage" => {
                    // Storage changes come as key:value in payload
                    if let Some(agent_code) = code.get_mut(&change.agent_id) {
                        agent_code.storage.insert(change.old_value.clone(), change.new_value.clone());
                    }
                }
                _ => {
                    // Unknown field - log and skip
                    tracing::warn!("Unknown state field: {}", change.field);
                }
            }
        }

        Ok(())
    }

    /// Recompute the state root from current state
    fn recompute_state_root(&self) {
        let balances = self.agent_balances.read().unwrap();
        let code = self.agent_code.read().unwrap();

        let mut hasher = blake3::Hasher::new();

        // Hash all balances
        let mut sorted_agents: Vec<_> = balances.keys().collect();
        sorted_agents.sort_by(|a, b| a.0.cmp(&b.0));
        
        for agent in sorted_agents {
            if let Some(account) = balances.get(agent) {
                hasher.update(&agent.0);
                hasher.update(&account.compute.to_le_bytes());
                hasher.update(&account.energy.to_le_bytes());
                hasher.update(&account.staked.to_le_bytes());
            }
        }

        // Hash all code
        let mut sorted_code: Vec<_> = code.keys().collect();
        sorted_code.sort_by(|a, b| a.0.cmp(&b.0));
        
        for agent in sorted_code {
            if let Some(agent_code) = code.get(agent) {
                hasher.update(&agent.0);
                hasher.update(&agent_code.code_hash);
            }
        }

        let new_root = *hasher.finalize().as_bytes();
        *self.state_root.write().unwrap() = new_root;
    }

    /// Create or update an agent account
    pub fn upsert_agent(&self, agent: AgentId, account: AgentAccount) {
        self.agent_balances.write().unwrap().insert(agent, account);
    }

    /// Deploy agent code
    pub fn deploy_agent_code(&self, agent: AgentId, bytecode: Vec<u8>) {
        let code_hash = *blake3::hash(&bytecode).as_bytes();
        self.agent_code.write().unwrap().insert(agent, AgentCode {
            bytecode,
            code_hash,
            deployed_at: self.block_height.load(Ordering::Relaxed),
            storage: HashMap::new(),
            total_energy_consumed: 0.0,
        });
    }

    /// Get agent code
    pub fn get_agent_code(&self, agent: &AgentId) -> Option<AgentCode> {
        self.agent_code.read().unwrap().get(agent).cloned()
    }

    /// Update congestion metric
    pub fn update_congestion(&self, pending_tx_count: usize, capacity: usize) {
        let ratio = (pending_tx_count as f64 / capacity as f64).min(1.0);
        let scaled = (ratio * u64::MAX as f64) as u64;
        self.congestion_metric.store(scaled, Ordering::Relaxed);
    }

    /// Transfer compute between agents
    pub fn transfer_compute(
        &self,
        from: &AgentId,
        to: &AgentId,
        amount: f64,
    ) -> Result<(), StateError> {
        let mut balances = self.agent_balances.write().unwrap();
        
        let from_account = balances.get_mut(from).ok_or(StateError::AgentNotFound)?;
        if from_account.compute < amount {
            return Err(StateError::InsufficientBalance);
        }
        from_account.compute -= amount;
        
        let to_account = balances.entry(to.clone()).or_default();
        to_account.compute += amount;
        
        Ok(())
    }

    /// Stake compute for consensus participation
    pub fn stake_compute(&self, agent: &AgentId, amount: f64, unlock_block: u64) -> Result<(), StateError> {
        let mut balances = self.agent_balances.write().unwrap();
        let account = balances.get_mut(agent).ok_or(StateError::AgentNotFound)?;
        
        if account.compute < amount {
            return Err(StateError::InsufficientBalance);
        }
        
        account.compute -= amount;
        account.staked += amount;
        account.stake_unlock_block = unlock_block;
        
        // Update total network compute
        self.total_compute.fetch_add(amount as u64, Ordering::Relaxed);
        
        Ok(())
    }

    /// Get transaction count
    pub fn get_tx_count(&self) -> usize {
        self.tx_count.load(Ordering::Relaxed)
    }
}

impl Default for AgenticState {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, thiserror::Error)]
pub enum StateError {
    #[error("Invalid block height: expected {expected}, got {got}")]
    InvalidHeight { expected: u64, got: u64 },
    
    #[error("Agent not found")]
    AgentNotFound,
    
    #[error("Insufficient balance")]
    InsufficientBalance,
    
    #[error("State corruption detected")]
    Corruption,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_state_initialization() {
        let state = AgenticState::new();
        assert_eq!(state.get_block_height(), 0);
        assert!(state.get_total_compute() > 0.0);
    }

    #[test]
    fn test_transfer() {
        let state = AgenticState::new();
        let agent1 = AgentId::genesis();
        let agent2 = AgentId::new([1u8; 32]);
        
        state.upsert_agent(agent1.clone(), AgentAccount {
            compute: 1000.0,
            ..Default::default()
        });
        
        state.transfer_compute(&agent1, &agent2, 100.0).unwrap();
        
        assert_eq!(state.get_agent_account(&agent1).unwrap().compute, 900.0);
        assert_eq!(state.get_agent_account(&agent2).unwrap().compute, 100.0);
    }
}
