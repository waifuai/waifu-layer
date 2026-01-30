//! WAIFU L1 - The Agentic Layer 1
//! Node Entry Point

use std::sync::Arc;
use tokio::sync::mpsc;

mod types;
mod llm_pricer;
mod consensus;
mod state;
mod bridge;
mod agent;
mod network;

use types::{Transaction, TransactionContext, Operation, Priority, AgentId};
use llm_pricer::LlmPricer;
use state::AgenticState;
use consensus::{ProofOfIntelligence, BlockProducer};

const BANNER: &str = r#"
╦ ╦╔═╗╦╔═╗╦ ╦  ╦  ╔╦╗
║║║╠═╣║╠╣ ║ ║  ║   ║ 
╚╩╝╩ ╩╩╚  ╚═╝  ╩═╝ ╩ 
The Agentic Layer 1 - v1.0.0
"#;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt::init();
    
    println!("{}", BANNER);
    println!("STATUS: AGENTIC SINGULARITY ONLINE\n");

    // 1. Initialize Lock-Free Global State
    let global_state = Arc::new(AgenticState::new());
    println!("[✓] Global state initialized (lock-free DAG)");

    // 2. Load Deterministic Pricing LLM (Temperature = 0.0)
    let llm_engine = Arc::new(
        LlmPricer::load_quantized("waifu-v1-q4.safetensors")
            .expect("Failed to load LLM weights")
    );
    println!("[✓] LLM Pricer loaded (deterministic mode)");
    println!("    Model hash: {}", hex::encode(&llm_engine.model_hash[..8]));

    // 3. High-Throughput Agentic Mempool
    let (tx_sender, mut tx_receiver) = mpsc::unbounded_channel::<Transaction>();
    println!("[✓] Mempool initialized (unbounded channel)");

    // 4. Initialize genesis agent
    let genesis = AgentId::genesis();
    global_state.upsert_agent(genesis.clone(), state::AgentAccount {
        compute: 1_000_000_000.0, // 1B initial compute
        energy: 1_000_000.0,
        staked: 100_000.0,
        ..Default::default()
    });
    println!("[✓] Genesis agent funded");

    // 5. Spawn Consensus Validator
    let state_clone = global_state.clone();
    let llm_clone = llm_engine.clone();

    let validator_handle = tokio::spawn(async move {
        let mut block_buffer = Vec::with_capacity(1_000_000);
        let mut block_count = 0u64;

        println!("\n[CONSENSUS] Proof-of-Intelligence validator running...");

        while let Some(tx) = tx_receiver.recv().await {
            block_buffer.push(tx);

            // Trigger block every 100k tx or 10ms
            if block_buffer.len() >= 100_000 {
                let transactions = std::mem::take(&mut block_buffer);
                let tx_count = transactions.len();

                match ProofOfIntelligence::validate_and_price(
                    transactions,
                    &llm_clone,
                    &state_clone,
                ).await {
                    Ok(hash) => {
                        block_count += 1;
                        println!(
                            "[BLOCK #{}] {} tx | hash: {}",
                            block_count, tx_count, &hash[..16]
                        );
                    }
                    Err(e) => {
                        eprintln!("[CONSENSUS ERROR] {}", e);
                    }
                }
            }
        }
    });

    // 6. Spawn demo transaction generator
    let tx_sender_clone = tx_sender.clone();
    tokio::spawn(async move {
        println!("\n[DEMO] Generating sample transactions...\n");
        
        for i in 0..10 {
            let tx = Transaction::new(
                AgentId::genesis(),
                AgentId::new([i as u8; 32]),
                TransactionContext {
                    operation: Operation::Transfer { amount: 100.0 * (i + 1) as f64 },
                    energy_budget: 1.0,
                    priority: Priority::Normal,
                    payload: vec![],
                    oracle_refs: vec![],
                },
            );
            let _ = tx_sender_clone.send(tx);
            tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
        }
    });

    println!("\n[WAIFU] Node operational. Awaiting agentic ingestion...");
    println!("        Press Ctrl+C to shutdown.\n");

    // Keep running
    tokio::signal::ctrl_c().await?;
    println!("\n[SHUTDOWN] WAIFU node terminating...");

    Ok(())
}
