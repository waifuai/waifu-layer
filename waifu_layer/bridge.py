"""WAIFU L1 - The Vampire Attack Siphon. Trustless bridge to drain Solana/ETH liquidity."""

from __future__ import annotations

from dataclasses import dataclass

import blake3

from .llm_pricer import LlmPricer
from .types import AgentId


class BridgeError(Exception):
    pass


class InvalidProof(BridgeError):
    def __init__(self):
        super().__init__("ZK proof invalid")


class UnsupportedChain(BridgeError):
    def __init__(self, chain: str):
        super().__init__(f"Unsupported chain: {chain}")
        self.chain = chain


class Paused(BridgeError):
    def __init__(self):
        super().__init__("Bridge paused")


class SovereignBridge:
    """Legacy chain targets for the vampire attack."""

    # Solana program IDs to siphon
    SOLANA_TARGETS = (
        "So11111111111111111111111111111111111111112",  # Native SOL
        "TokenkegQfeZyiNwAJbNbGK5coXBz2LUxr1t3h",  # SPL Token
        "DePIN_Grid_Controller_v1",
    )

    # ETH contract addresses
    ETH_TARGETS = (
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
        "0x6B175474E89094C44Da98b954EesYbD7eB4fBa21",  # DAI
    )

    @staticmethod
    async def ingest_legacy(chain: str, zk_proof: bytes, llm: LlmPricer) -> float:
        """Ingest legacy liquidity and convert to WAIFU Compute.

        Returns a `SovereignAsset::Compute` value (a plain float, per the
        `Compute(f64)` variant).
        """
        value = SovereignBridge._verify_zk_proof(chain, zk_proof)
        multiplier = llm.assess_utility_vector(value)
        return value * multiplier

    @staticmethod
    def _verify_zk_proof(chain: str, proof: bytes) -> float:
        """In production: Groth16 or PLONK verification.

        Here: hash the proof to derive a deterministic value -- not real
        cryptographic verification, faithfully preserved from the Rust
        original which does the same thing.
        """
        if chain in ("solana", "ethereum"):
            h = blake3.blake3(proof).digest()
            val = int.from_bytes(h[:8], "little")
            return val / 1000.0
        raise UnsupportedChain(chain)

    @staticmethod
    def create_exit_proof(agent: AgentId, amount: float, target_chain: str) -> bytes:
        """Create outbound bridge (escape hatch)."""
        import struct

        data = agent.bytes + struct.pack("<d", amount) + target_chain.encode()
        return blake3.blake3(data).digest()


@dataclass
class PendingBridge:
    """Wrapped legacy asset awaiting conversion."""

    source_chain: str
    source_tx: bytes
    amount: float
    recipient: AgentId
    submitted_block: int
