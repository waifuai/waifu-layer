//! WAIFU L1 - Mesh Network
//! libp2p + QUIC for unblockable agent-to-agent streaming

use crate::types::{NetworkMessage, AgentId, Transaction, Block};
use libp2p::{
    gossipsub, identity, mdns,
    swarm::NetworkBehaviour,
    PeerId,
};
use std::collections::HashSet;
use tokio::sync::mpsc;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum NetworkError {
    #[error("Transport error: {0}")]
    Transport(String),
    #[error("Peer not found")]
    PeerNotFound,
    #[error("Broadcast failed")]
    BroadcastFailed,
}

/// The P2P network behavior
#[derive(NetworkBehaviour)]
pub struct WaifuBehaviour {
    gossipsub: gossipsub::Behaviour,
    mdns: mdns::tokio::Behaviour,
}

/// WAIFU network node
pub struct WaifuNetwork {
    pub local_peer_id: PeerId,
    pub agent_id: AgentId,
    connected_peers: HashSet<PeerId>,
    tx_sender: mpsc::UnboundedSender<Transaction>,
    block_sender: mpsc::UnboundedSender<Block>,
}

impl WaifuNetwork {
    pub async fn new(
        agent_id: AgentId,
        tx_sender: mpsc::UnboundedSender<Transaction>,
        block_sender: mpsc::UnboundedSender<Block>,
    ) -> Result<Self, NetworkError> {
        let local_key = identity::Keypair::generate_ed25519();
        let local_peer_id = PeerId::from(local_key.public());

        Ok(Self {
            local_peer_id,
            agent_id,
            connected_peers: HashSet::new(),
            tx_sender,
            block_sender,
        })
    }

    pub fn peer_count(&self) -> usize {
        self.connected_peers.len()
    }

    pub fn add_peer(&mut self, peer: PeerId) {
        self.connected_peers.insert(peer);
    }

    pub fn remove_peer(&mut self, peer: &PeerId) {
        self.connected_peers.remove(peer);
    }

    /// Broadcast transaction to all peers
    pub async fn broadcast_tx(&self, tx: &Transaction) -> Result<(), NetworkError> {
        // Would publish to gossipsub topic
        Ok(())
    }

    /// Broadcast block to all peers
    pub async fn broadcast_block(&self, block: &Block) -> Result<(), NetworkError> {
        Ok(())
    }

    /// Handle incoming message
    pub fn handle_message(&self, msg: NetworkMessage) {
        match msg {
            NetworkMessage::NewTransaction(tx) => {
                let _ = self.tx_sender.send(tx);
            }
            NetworkMessage::NewBlock(block) => {
                let _ = self.block_sender.send(block);
            }
            _ => {}
        }
    }
}

/// Bootstrap nodes for initial peer discovery
pub const BOOTSTRAP_NODES: [&str; 3] = [
    "/ip4/0.0.0.0/tcp/9000",
    "/ip4/0.0.0.0/tcp/9001", 
    "/ip4/0.0.0.0/tcp/9002",
];
