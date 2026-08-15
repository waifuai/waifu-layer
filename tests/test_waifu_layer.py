"""Python port of the inline Rust unit tests from types.rs, state.rs, llm_pricer.rs."""

from waifu_layer.llm_pricer import LlmPricer
from waifu_layer.state import AgentAccount, AgenticState
from waifu_layer.types import AgentId, Operation, Priority, Transaction, TransactionContext


def test_agent_id_creation():
    pk = bytes([1] * 32)
    agent = AgentId.from_public_key(pk)
    assert agent.bytes != bytes(32)


def test_transaction_hash_determinism():
    tx = Transaction.new(
        AgentId.genesis(),
        AgentId.genesis(),
        TransactionContext(
            operation=Operation.transfer(100.0),
            energy_budget=1.0,
            priority=Priority.NORMAL,
            payload=b"",
            oracle_refs=[],
        ),
    )
    hash1 = tx.hash()
    hash2 = tx.hash()
    assert hash1 == hash2


def test_state_initialization():
    state = AgenticState()
    assert state.get_block_height() == 0
    assert state.get_total_compute() > 0.0


def test_transfer():
    state = AgenticState()
    agent1 = AgentId.genesis()
    agent2 = AgentId(bytes([1] * 32))

    state.upsert_agent(agent1, AgentAccount(compute=1000.0))
    state.transfer_compute(agent1, agent2, 100.0)

    assert state.get_agent_account(agent1).compute == 900.0
    assert state.get_agent_account(agent2).compute == 100.0


def test_pricer_determinism():
    pricer = LlmPricer.load_quantized("test-model.safetensors")
    assert pricer.is_deterministic()

    state = AgenticState()
    tx = Transaction.new(
        AgentId.genesis(),
        AgentId.genesis(),
        TransactionContext(
            operation=Operation.transfer(100.0),
            energy_budget=1.0,
            priority=Priority.NORMAL,
            payload=b"",
            oracle_refs=[],
        ),
    )

    # Same transaction should always get same price
    price1, _ = pricer.price_transaction(tx, state)
    price2, _ = pricer.price_transaction(tx, state)
    assert price1 == price2
