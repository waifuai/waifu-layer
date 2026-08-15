"""WAIFU L1 - The Agentic Layer 1. Node Entry Point."""

from __future__ import annotations

import asyncio
import logging

from .consensus import ProofOfIntelligence
from .llm_pricer import LlmPricer
from .state import AgentAccount, AgenticState
from .types import AgentId, Operation, Priority, Transaction, TransactionContext

BANNER = r"""
╦ ╦╔═╗╦╔═╗╦ ╦  ╦  ╔╦╗
║║║╠═╣║╠╣ ║ ║  ║   ║
╚╩╝╩ ╩╩╚  ╚═╝  ╩═╝ ╩
The Agentic Layer 1 - v1.0.0
"""


async def _validator_loop(tx_queue: "asyncio.Queue[Transaction]", llm_engine: LlmPricer, global_state: AgenticState) -> None:
    block_buffer: list[Transaction] = []
    block_count = 0

    print("\n[CONSENSUS] Proof-of-Intelligence validator running...")

    while True:
        tx = await tx_queue.get()
        block_buffer.append(tx)

        # Trigger block every 100k tx
        if len(block_buffer) >= 100_000:
            transactions, block_buffer = block_buffer, []
            tx_count = len(transactions)

            try:
                block_hash = await ProofOfIntelligence.validate_and_price(transactions, llm_engine, global_state)
                block_count += 1
                print(f"[BLOCK #{block_count}] {tx_count} tx | hash: {block_hash[:16]}")
            except Exception as e:
                print(f"[CONSENSUS ERROR] {e}")


async def _demo_generator(tx_queue: "asyncio.Queue[Transaction]") -> None:
    print("\n[DEMO] Generating sample transactions...\n")

    for i in range(10):
        tx = Transaction.new(
            AgentId.genesis(),
            AgentId(bytes([i]) + bytes(31)),
            TransactionContext(
                operation=Operation.transfer(100.0 * (i + 1)),
                energy_budget=1.0,
                priority=Priority.NORMAL,
                payload=b"",
                oracle_refs=[],
            ),
        )
        await tx_queue.put(tx)
        await asyncio.sleep(0.1)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    print(BANNER)
    print("STATUS: AGENTIC SINGULARITY ONLINE\n")

    # 1. Initialize Lock-Free Global State
    global_state = AgenticState()
    print("[✓] Global state initialized (lock-free DAG)")

    # 2. Load Deterministic Pricing LLM (Temperature = 0.0)
    llm_engine = LlmPricer.load_quantized("waifu-v1-q4.safetensors")
    print("[✓] LLM Pricer loaded (deterministic mode)")
    print(f"    Model hash: {llm_engine.model_hash[:8].hex()}")

    # 3. High-Throughput Agentic Mempool
    tx_queue: "asyncio.Queue[Transaction]" = asyncio.Queue()
    print("[✓] Mempool initialized (unbounded queue)")

    # 4. Initialize genesis agent
    genesis = AgentId.genesis()
    global_state.upsert_agent(genesis, AgentAccount(
        compute=1_000_000_000.0,  # 1B initial compute
        energy=1_000_000.0,
        staked=100_000.0,
    ))
    print("[✓] Genesis agent funded")

    # 5. Spawn Consensus Validator
    validator_task = asyncio.create_task(_validator_loop(tx_queue, llm_engine, global_state))

    # 6. Spawn demo transaction generator
    demo_task = asyncio.create_task(_demo_generator(tx_queue))

    print("\n[WAIFU] Node operational. Awaiting agentic ingestion...")
    print("        Press Ctrl+C to shutdown.\n")

    # Keep running
    try:
        await asyncio.gather(validator_task, demo_task)
    except asyncio.CancelledError:
        pass
    finally:
        print("\n[SHUTDOWN] WAIFU node terminating...")


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] WAIFU node terminating...")


if __name__ == "__main__":
    run()
