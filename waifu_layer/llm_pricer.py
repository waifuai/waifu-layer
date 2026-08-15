"""WAIFU L1 - The Oracle of Truth.

LLM-based pricing engine that replaces AMMs and order books.

NOTE: despite the name, this is not real model inference. `load_quantized`
never loads real weights -- it fabricates deterministic dummy tensors, and
`model_hash` is just blake3(model_path), not a hash of actual weights.
`price_transaction` hand-encodes a feature vector and runs two matmuls
against those dummy tensors, i.e. this is dense linear algebra dressed up
as "LLM inference," faithfully preserved from the Rust original (which used
candle purely as a tensor-math library the same way). numpy is a faithful
substitute for candle here for exactly that reason.
"""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor

import blake3
import numpy as np

from .state import AgenticState
from .types import AgentId, Priority, Transaction, TransactionContext


class PricerError(Exception):
    pass


class LlmPricer:
    """The deterministic LLM pricing engine. Temperature = 0.0 for consensus-compatible inference."""

    def __init__(self, device_note: str, model_hash: bytes, embed_dim: int,
                 context_weights: np.ndarray, operation_matrices: list[np.ndarray]):
        self.device_note = device_note
        self.model_hash = model_hash
        self.embed_dim = embed_dim
        self.context_weights = context_weights
        self.operation_matrices = operation_matrices
        self.temperature = 0.0  # CRITICAL: Must be 0 for consensus

    @staticmethod
    def load_quantized(model_path: str) -> "LlmPricer":
        """Load a "quantized model" from safetensors format.

        In production, this loads actual quantized transformer weights. For
        now, initializes with deterministic pseudo-random weights.
        """
        embed_dim = 768

        model_hash = blake3.blake3(model_path.encode()).digest()

        context_weights = np.ones((embed_dim, 64), dtype=np.float32)

        operation_matrices = [
            (np.ones((embed_dim, embed_dim), dtype=np.float32) * (1.0 / (i + 1.0)))
            for i in range(8)
        ]

        return LlmPricer(
            device_note="cpu",
            model_hash=model_hash,
            embed_dim=embed_dim,
            context_weights=context_weights,
            operation_matrices=operation_matrices,
        )

    def price_transaction(self, tx: Transaction, state: AgenticState) -> tuple[float, str]:
        """Price a transaction based on its context and current network state.

        Returns (clearing_rate, pricing_rationale).
        """
        # 1. Encode the transaction context into a tensor
        context_embedding = self._encode_context(tx.context)

        # 2. Get the operation-specific pricing matrix
        op_matrix = self._get_operation_matrix(tx.context.operation)

        # 3. Query network state for supply/demand signals
        network_signal = self._compute_network_signal(state, tx.from_, tx.to)

        # 4. Perform deterministic matrix multiplication (THE CORE PRICING)
        price_vector = context_embedding @ op_matrix @ self.context_weights

        # 5. Reduce to scalar clearing rate
        raw_price = float(price_vector.sum())

        # 6. Apply network signal modulation
        clearing_rate = self._normalize_price(raw_price, network_signal, tx.context)

        # 7. Generate pricing rationale (deterministic)
        rationale = self._generate_rationale(tx.context, clearing_rate, network_signal)

        return clearing_rate, rationale

    def _encode_context(self, context: TransactionContext) -> np.ndarray:
        """Encode transaction context into embedding space."""
        features = np.zeros(self.embed_dim, dtype=np.float32)

        features[0] = context.energy_budget

        priority_idx = {
            Priority.LOW: 1,
            Priority.NORMAL: 2,
            Priority.HIGH: 3,
            Priority.CRITICAL: 4,
        }[context.priority]
        features[priority_idx] = 1.0

        op = context.operation
        if op.kind == "Transfer":
            features[10] = op.amount
            op_idx = 10
        elif op.kind == "Execute":
            op_idx = 20
        elif op.kind == "Deploy":
            features[30] = op.initial_energy
            op_idx = 30
        elif op.kind == "Bridge":
            op_idx = 40
        elif op.kind == "Stake":
            features[50] = op.amount
            op_idx = 50
        elif op.kind == "Infer":
            features[60] = op.max_tokens
            op_idx = 60
        elif op.kind == "Swap":
            op_idx = 70
        else:
            raise PricerError(f"unknown operation kind: {op.kind}")
        features[op_idx] = 1.0

        features[100] = len(context.payload) / 1024.0
        features[101] = len(context.oracle_refs)

        return features.reshape(1, self.embed_dim)

    def _get_operation_matrix(self, operation) -> np.ndarray:
        """Get the appropriate pricing matrix for an operation type."""
        idx = {
            "Transfer": 0, "Execute": 1, "Deploy": 2, "Bridge": 3,
            "Stake": 4, "Infer": 5, "Swap": 6,
        }[operation.kind]
        return self.operation_matrices[min(idx, len(self.operation_matrices) - 1)]

    def _compute_network_signal(self, state: AgenticState, from_: AgentId, to: AgentId) -> float:
        """Compute network-level supply/demand signal."""
        sender_stake = state.get_agent_stake(from_)
        receiver_stake = state.get_agent_stake(to)

        congestion = state.get_network_congestion()
        total_compute = state.get_total_compute()

        reputation_factor = math.log1p(sender_stake + receiver_stake)
        congestion_factor = 1.0 + (congestion * 2.0)
        compute_factor = math.sqrt(total_compute / 1_000_000.0)

        return reputation_factor * congestion_factor / max(compute_factor, 1.0)

    def _normalize_price(self, raw: float, network_signal: float, context: TransactionContext) -> float:
        """Normalize raw price to usable clearing rate."""
        base = abs(raw) / (self.embed_dim * 64.0)
        signaled = base * (1.0 + network_signal)

        priority_mult = {
            Priority.LOW: 0.8,
            Priority.NORMAL: 1.0,
            Priority.HIGH: 1.5,
            Priority.CRITICAL: 2.5,
        }[context.priority]

        return min(max(signaled * priority_mult, 0.0001), 1_000_000.0)

    def _generate_rationale(self, context: TransactionContext, clearing_rate: float, network_signal: float) -> str:
        """Generate deterministic pricing rationale."""
        op = context.operation
        if op.kind == "Transfer":
            op_name = f"TRANSFER({op.amount:.2f})"
        elif op.kind == "Execute":
            op_name = f"EXECUTE({op.function})"
        elif op.kind == "Deploy":
            op_name = "DEPLOY"
        elif op.kind == "Bridge":
            op_name = f"BRIDGE({op.source_chain})"
        elif op.kind == "Stake":
            op_name = f"STAKE({op.amount:.2f})"
        elif op.kind == "Infer":
            op_name = f"INFER({op.max_tokens})"
        elif op.kind == "Swap":
            op_name = "SWAP"
        else:
            op_name = op.kind

        priority_debug = {
            Priority.LOW: "Low", Priority.NORMAL: "Normal",
            Priority.HIGH: "High", Priority.CRITICAL: "Critical",
        }[context.priority]

        return (
            f"PoI-PRICE: {op_name} @ {clearing_rate:.6f} | NET_SIG: {network_signal:.4f} "
            f"| PRI: {priority_debug} | ENERGY: {context.energy_budget:.2f}"
        )

    def assess_utility_vector(self, legacy_value: float) -> float:
        """Assess the utility value of a legacy asset being bridged.

        AI utility tokens get a premium, memecoins get discounted. In
        production, this would query the agent's historical performance.
        """
        base_rate = 0.95
        scale_factor = min(math.log1p(legacy_value) / 10.0, 1.2)
        return base_rate * scale_factor

    def price_batch(self, transactions: list[Transaction], state: AgenticState) -> list[tuple[float, str] | Exception]:
        """Batch price multiple transactions for parallel execution.

        Uses a thread pool to mirror rayon::par_iter's intent -- note Python
        threads won't get true CPU parallelism for the pure-Python parts due
        to the GIL, though numpy's matmul releases the GIL during the actual
        computation, so there is real parallelism during the pricing step
        itself.
        """
        with ThreadPoolExecutor() as pool:
            def price_or_error(tx: Transaction):
                try:
                    return self.price_transaction(tx, state)
                except PricerError as e:
                    return e

            return list(pool.map(price_or_error, transactions))

    def get_model_hash(self) -> bytes:
        return self.model_hash

    def is_deterministic(self) -> bool:
        """Verify that inference is deterministic (temperature = 0)."""
        return self.temperature == 0.0
