"""WAIFU L1 - Mesh Network.

The Rust original declared libp2p (gossipsub + mdns) data structures, but
`broadcast_tx`/`broadcast_block` were already inert stubs there (`Ok(())`
with no swarm/transport ever built), and `main.rs` never constructed or
wired in a `WaifuNetwork` at all. This preserves that: a lightweight,
dependency-free stand-in for the peer/PeerId bookkeeping, still unwired
and still just as inert. A real implementation would need an actual
libp2p-equivalent transport (e.g. Python's `libp2p` package or a custom
QUIC/gossipsub stack), which was never present here either.
"""

from __future__ import annotations

import queue
import secrets
from dataclasses import dataclass, field

from .types import AgentId, Block, NetworkMessage, Transaction


class NetworkError(Exception):
    pass


class Transport(NetworkError):
    def __init__(self, detail: str):
        super().__init__(f"Transport error: {detail}")


class PeerNotFound(NetworkError):
    def __init__(self):
        super().__init__("Peer not found")


class BroadcastFailed(NetworkError):
    def __init__(self):
        super().__init__("Broadcast failed")


@dataclass(frozen=True)
class PeerId:
    """Simplified stand-in for libp2p's PeerId (derived from a random identity, not a real keypair)."""

    identity: bytes

    @staticmethod
    def generate() -> "PeerId":
        return PeerId(secrets.token_bytes(32))

    def __str__(self) -> str:
        return self.identity.hex()

    def __hash__(self) -> int:
        return hash(self.identity)


class WaifuNetwork:
    """WAIFU network node."""

    def __init__(self, agent_id: AgentId, tx_sender: "queue.Queue[Transaction]", block_sender: "queue.Queue[Block]"):
        self.local_peer_id = PeerId.generate()
        self.agent_id = agent_id
        self._connected_peers: set[PeerId] = set()
        self._tx_sender = tx_sender
        self._block_sender = block_sender

    @staticmethod
    async def new(agent_id: AgentId, tx_sender: "queue.Queue[Transaction]", block_sender: "queue.Queue[Block]") -> "WaifuNetwork":
        return WaifuNetwork(agent_id, tx_sender, block_sender)

    def peer_count(self) -> int:
        return len(self._connected_peers)

    def add_peer(self, peer: PeerId) -> None:
        self._connected_peers.add(peer)

    def remove_peer(self, peer: PeerId) -> None:
        self._connected_peers.discard(peer)

    async def broadcast_tx(self, tx: Transaction) -> None:
        """Broadcast transaction to all peers. Would publish to a gossipsub topic."""
        return None

    async def broadcast_block(self, block: Block) -> None:
        """Broadcast block to all peers."""
        return None

    def handle_message(self, msg: NetworkMessage) -> None:
        """Handle incoming message."""
        if msg.kind == "NewTransaction":
            self._tx_sender.put(msg.transaction)
        elif msg.kind == "NewBlock":
            self._block_sender.put(msg.block)


# Bootstrap nodes for initial peer discovery
BOOTSTRAP_NODES = (
    "/ip4/0.0.0.0/tcp/9000",
    "/ip4/0.0.0.0/tcp/9001",
    "/ip4/0.0.0.0/tcp/9002",
)
