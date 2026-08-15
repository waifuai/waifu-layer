"""WAIFU L1 - Proof-of-Intelligence Consensus."""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass

from .llm_pricer import LlmPricer, PricerError
from .state import AgenticState, StateError
from .types import AgentId, Block, ExecutionResult, Operation, PoIProof, PricedTransaction, Transaction


class ConsensusError(Exception):
    pass


class PricingError(ConsensusError):
    def __init__(self, cause: PricerError):
        super().__init__(f"Pricing failed: {cause}")
        self.cause = cause


class ValidationFailed(ConsensusError):
    def __init__(self, detail: str):
        super().__init__(f"Block validation failed: {detail}")


class NonDeterministic(ConsensusError):
    def __init__(self):
        super().__init__("Non-deterministic inference")


@dataclass
class ProofOfIntelligence:
    min_stake: float = 1000.0
    block_time_ns: int = 10_000_000
    max_tx_per_block: int = 100_000

    @staticmethod
    async def validate_and_price(transactions: list[Transaction], llm: LlmPricer, state: AgenticState) -> str:
        if not llm.is_deterministic():
            raise NonDeterministic()

        # Parallel pricing via a thread pool (rayon::par_iter equivalent -- see llm_pricer.price_batch)
        priced: list[PricedTransaction] = []
        for tx, outcome in zip(transactions, llm.price_batch(transactions, state)):
            if isinstance(outcome, Exception):
                continue
            price, rationale = outcome
            result = ProofOfIntelligence._execute_tx(tx, price, state)
            priced.append(PricedTransaction(original=tx, clearing_rate=price, pricing_rationale=rationale, result=result))

        llm_root = ProofOfIntelligence._compute_llm_root(priced, llm)
        poi = ProofOfIntelligence._create_poi(llm, priced)

        block = Block(
            height=state.get_block_height() + 1,
            hash=bytes(32),
            parents=state.get_dag_tips(),
            transactions=priced,
            llm_state_root=llm_root,
            validator=AgentId.genesis(),
            poi_proof=poi,
            timestamp=time.time_ns(),
        )

        block_hash = block.compute_hash()
        block.hash = block_hash

        try:
            state.apply_block(block)
        except StateError as e:
            raise ValidationFailed(str(e)) from e

        return block_hash.hex()

    @staticmethod
    def _execute_tx(tx: Transaction, rate: float, state: AgenticState) -> ExecutionResult:
        op: Operation = tx.context.operation
        if op.kind == "Transfer":
            try:
                state.transfer_compute(tx.from_, tx.to, op.amount)
                return ExecutionResult.success_result(gas_used=rate)
            except StateError as e:
                return ExecutionResult.failure(reason=str(e), gas_used=rate * 0.5)
        return ExecutionResult.success_result(gas_used=rate)

    @staticmethod
    def _compute_llm_root(txs: list[PricedTransaction], llm: LlmPricer) -> bytes:
        import blake3

        h = blake3.blake3()
        h.update(llm.get_model_hash())
        for tx in txs:
            h.update(_f64_le(tx.clearing_rate))
        return h.digest()

    @staticmethod
    def _create_poi(llm: LlmPricer, txs: list[PricedTransaction]) -> PoIProof:
        import blake3

        ih = blake3.blake3()
        oh = blake3.blake3()
        for tx in txs:
            ih.update(tx.original.hash())
            oh.update(_f64_le(tx.clearing_rate))
        return PoIProof(
            model_hash=llm.get_model_hash(),
            input_hash=ih.digest(),
            output_hash=oh.digest(),
            temperature=0.0,
            signature=bytes(64),
        )


class BlockProducer:
    def __init__(self, validator_id: AgentId):
        self.validator_id = validator_id
        self._pending: "queue.Queue[Transaction]" = queue.Queue()

    def submit(self, tx: Transaction) -> None:
        self._pending.put(tx)

    def pending_count(self) -> int:
        return self._pending.qsize()

    async def produce(self, llm: LlmPricer, state: AgenticState) -> str:
        txs: list[Transaction] = []
        while len(txs) < 100_000:
            try:
                txs.append(self._pending.get_nowait())
            except queue.Empty:
                break
        if not txs:
            raise ValidationFailed("empty")
        return await ProofOfIntelligence.validate_and_price(txs, llm, state)


def _f64_le(value: float) -> bytes:
    import struct

    return struct.pack("<d", value)
