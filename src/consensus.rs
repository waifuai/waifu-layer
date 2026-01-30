//! WAIFU L1 - Proof-of-Intelligence Consensus

use crate::types::*;
use crate::llm_pricer::{LlmPricer, PricerError};
use crate::state::AgenticState;
use rayon::prelude::*;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ConsensusError {
    #[error("Pricing failed: {0}")]
    PricingError(#[from] PricerError),
    #[error("Invalid PoI proof: {0}")]
    InvalidProof(String),
    #[error("Block validation failed: {0}")]
    ValidationFailed(String),
    #[error("Non-deterministic inference")]
    NonDeterministic,
}

pub struct ProofOfIntelligence {
    pub min_stake: f64,
    pub block_time_ns: u128,
    pub max_tx_per_block: usize,
}

impl Default for ProofOfIntelligence {
    fn default() -> Self {
        Self {
            min_stake: 1000.0,
            block_time_ns: 10_000_000,
            max_tx_per_block: 100_000,
        }
    }
}

impl ProofOfIntelligence {
    pub async fn validate_and_price(
        transactions: Vec<Transaction>,
        llm: &Arc<LlmPricer>,
        state: &Arc<AgenticState>,
    ) -> Result<String, ConsensusError> {
        if !llm.is_deterministic() {
            return Err(ConsensusError::NonDeterministic);
        }

        // Parallel pricing via rayon
        let priced: Vec<PricedTransaction> = transactions
            .par_iter()
            .filter_map(|tx| {
                let (price, rationale) = llm.price_transaction(tx, state).ok()?;
                let result = Self::execute_tx(tx, price, state);
                Some(PricedTransaction {
                    original: tx.clone(),
                    clearing_rate: price,
                    pricing_rationale: rationale,
                    result,
                })
            })
            .collect();

        let llm_root = Self::compute_llm_root(&priced, llm);
        let poi = Self::create_poi(llm, &priced);

        let block = Block {
            height: state.get_block_height() + 1,
            hash: [0u8; 32],
            parents: state.get_dag_tips(),
            transactions: priced,
            llm_state_root: llm_root,
            validator: AgentId::genesis(),
            poi_proof: poi,
            timestamp: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos(),
        };

        let hash = block.compute_hash();
        let mut final_block = block;
        final_block.hash = hash;

        state.apply_block(&final_block)
            .map_err(|e| ConsensusError::ValidationFailed(e.to_string()))?;

        Ok(hex::encode(hash))
    }

    fn execute_tx(tx: &Transaction, rate: f64, state: &AgenticState) -> ExecutionResult {
        match &tx.context.operation {
            Operation::Transfer { amount } => {
                match state.transfer_compute(&tx.from, &tx.to, *amount) {
                    Ok(_) => ExecutionResult::Success { 
                        gas_used: rate, 
                        state_changes: vec![] 
                    },
                    Err(e) => ExecutionResult::Failure { 
                        reason: e.to_string(), 
                        gas_used: rate * 0.5 
                    },
                }
            }
            _ => ExecutionResult::Success { gas_used: rate, state_changes: vec![] },
        }
    }

    fn compute_llm_root(txs: &[PricedTransaction], llm: &LlmPricer) -> [u8; 32] {
        let mut h = blake3::Hasher::new();
        h.update(&llm.get_model_hash());
        for tx in txs {
            h.update(&tx.clearing_rate.to_le_bytes());
        }
        *h.finalize().as_bytes()
    }

    fn create_poi(llm: &LlmPricer, txs: &[PricedTransaction]) -> PoIProof {
        let mut ih = blake3::Hasher::new();
        let mut oh = blake3::Hasher::new();
        for tx in txs {
            ih.update(&tx.original.hash());
            oh.update(&tx.clearing_rate.to_le_bytes());
        }
        PoIProof {
            model_hash: llm.get_model_hash(),
            input_hash: *ih.finalize().as_bytes(),
            output_hash: *oh.finalize().as_bytes(),
            temperature: 0.0,
            signature: [0u8; 64],
        }
    }
}

pub struct BlockProducer {
    pub validator_id: AgentId,
    pending: crossbeam::queue::SegQueue<Transaction>,
}

impl BlockProducer {
    pub fn new(id: AgentId) -> Self {
        Self { validator_id: id, pending: crossbeam::queue::SegQueue::new() }
    }

    pub fn submit(&self, tx: Transaction) { self.pending.push(tx); }
    pub fn pending_count(&self) -> usize { self.pending.len() }

    pub async fn produce(
        &self, llm: &Arc<LlmPricer>, state: &Arc<AgenticState>,
    ) -> Result<String, ConsensusError> {
        let mut txs = Vec::with_capacity(100_000);
        while let Some(tx) = self.pending.pop() {
            txs.push(tx);
            if txs.len() >= 100_000 { break; }
        }
        if txs.is_empty() {
            return Err(ConsensusError::ValidationFailed("empty".into()));
        }
        ProofOfIntelligence::validate_and_price(txs, llm, state).await
    }
}
