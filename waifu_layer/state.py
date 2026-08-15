"""WAIFU L1 - Lock-Free Global State.

No EVM bottlenecks - parallel state access via DAG reconciliation.

Python has no lock-free atomics or concurrent maps in the standard library,
so `crossbeam::SegQueue`/`AtomicU64`/`RwLock<HashMap>` are approximated with
`queue.Queue` and `threading.Lock`/`threading.RLock`-guarded plain values --
correct, but without the Rust version's true lock-free guarantees.
"""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass, field

import blake3

from .types import AgentId, Block, ExecutionResult, StateChange

logger = logging.getLogger("waifu_layer.state")


class StateError(Exception):
    pass


class InvalidHeight(StateError):
    def __init__(self, expected: int, got: int):
        super().__init__(f"Invalid block height: expected {expected}, got {got}")
        self.expected = expected
        self.got = got


class AgentNotFound(StateError):
    def __init__(self):
        super().__init__("Agent not found")


class InsufficientBalance(StateError):
    def __init__(self):
        super().__init__("Insufficient balance")


@dataclass
class AgentAccount:
    """Individual agent's account state."""

    compute: float = 0.0
    energy: float = 0.0
    staked: float = 0.0
    stake_unlock_block: int = 0
    reputation: float = 0.0
    nonce: int = 0
    equity_holdings: dict[AgentId, float] = field(default_factory=dict)


@dataclass
class AgentCode:
    """Deployed agent code and state."""

    bytecode: bytes
    code_hash: bytes
    deployed_at: int
    storage: dict[bytes, bytes] = field(default_factory=dict)
    total_energy_consumed: float = 0.0


class AgenticState:
    """The global agentic state - concurrent access guarded by locks."""

    U64_MAX = 2**64 - 1

    def __init__(self) -> None:
        self._balances_lock = threading.RLock()
        self._agent_balances: dict[AgentId, AgentAccount] = {}

        self._code_lock = threading.RLock()
        self._agent_code: dict[AgentId, AgentCode] = {}

        self._pending_changes: queue.Queue[StateChange] = queue.Queue()

        self._counters_lock = threading.Lock()
        self._block_height = 0
        self._congestion_metric = 0  # scaled to u64
        self._total_compute = 1_000_000_000  # 1B initial

        self._dag_lock = threading.RLock()
        self._dag_tips: list[bytes] = [bytes(32)]

        self._root_lock = threading.RLock()
        self._state_root = bytes(32)

        self._tx_count_lock = threading.Lock()
        self._tx_count = 0

    def get_agent_stake(self, agent: AgentId) -> float:
        """Get agent's staked compute (for pricing signals)."""
        with self._balances_lock:
            account = self._agent_balances.get(agent)
            return account.staked if account else 0.0

    def get_agent_account(self, agent: AgentId) -> AgentAccount | None:
        with self._balances_lock:
            account = self._agent_balances.get(agent)
            return AgentAccount(**vars(account)) if account else None

    def get_network_congestion(self) -> float:
        """Get network congestion (0.0 - 1.0)."""
        with self._counters_lock:
            raw = self._congestion_metric
        return raw / self.U64_MAX

    def get_total_compute(self) -> float:
        with self._counters_lock:
            return float(self._total_compute)

    def get_block_height(self) -> int:
        with self._counters_lock:
            return self._block_height

    def get_dag_tips(self) -> list[bytes]:
        with self._dag_lock:
            return list(self._dag_tips)

    def get_state_root(self) -> bytes:
        with self._root_lock:
            return self._state_root

    def apply_block(self, block: Block) -> None:
        """Apply a validated block to state."""
        # 1. Verify block height is valid
        with self._counters_lock:
            current_height = self._block_height
        if block.height != current_height + 1:
            raise InvalidHeight(current_height + 1, block.height)

        # 2. Apply all state changes from transactions
        for priced_tx in block.transactions:
            if priced_tx.result.success:
                for change in priced_tx.result.state_changes:
                    self._pending_changes.put(change)

        # 3. Process pending changes
        self._flush_pending_changes()

        # 4. Update block height
        with self._counters_lock:
            self._block_height = block.height

        # 5. Update DAG tips
        with self._dag_lock:
            self._dag_tips = [tip for tip in self._dag_tips if tip not in block.parents]
            self._dag_tips.append(block.hash)

        # 6. Update state root
        self._recompute_state_root()

        # 7. Update transaction count
        with self._tx_count_lock:
            self._tx_count += len(block.transactions)

    def _flush_pending_changes(self) -> None:
        """Flush pending state changes (batched for efficiency)."""
        with self._balances_lock, self._code_lock:
            while True:
                try:
                    change = self._pending_changes.get_nowait()
                except queue.Empty:
                    break

                if change.field == "compute":
                    account = self._agent_balances.setdefault(change.agent_id, AgentAccount())
                    try:
                        account.compute = float(change.new_value.decode("utf-8"))
                    except (UnicodeDecodeError, ValueError):
                        pass
                elif change.field == "energy":
                    account = self._agent_balances.setdefault(change.agent_id, AgentAccount())
                    try:
                        account.energy = float(change.new_value.decode("utf-8"))
                    except (UnicodeDecodeError, ValueError):
                        pass
                elif change.field == "staked":
                    account = self._agent_balances.setdefault(change.agent_id, AgentAccount())
                    try:
                        account.staked = float(change.new_value.decode("utf-8"))
                    except (UnicodeDecodeError, ValueError):
                        pass
                elif change.field == "reputation":
                    account = self._agent_balances.setdefault(change.agent_id, AgentAccount())
                    try:
                        account.reputation = float(change.new_value.decode("utf-8"))
                    except (UnicodeDecodeError, ValueError):
                        pass
                elif change.field == "code":
                    with self._counters_lock:
                        height = self._block_height
                    agent_code = self._agent_code.setdefault(
                        change.agent_id, AgentCode(bytecode=b"", code_hash=bytes(32), deployed_at=height)
                    )
                    agent_code.bytecode = change.new_value
                    agent_code.code_hash = blake3.blake3(change.new_value).digest()
                elif change.field == "storage":
                    # Storage changes come as key:value in payload
                    agent_code = self._agent_code.get(change.agent_id)
                    if agent_code is not None:
                        agent_code.storage[change.old_value] = change.new_value
                else:
                    logger.warning("Unknown state field: %s", change.field)

    def _recompute_state_root(self) -> None:
        """Recompute the state root from current state."""
        with self._balances_lock, self._code_lock:
            hasher = blake3.blake3()

            for agent in sorted(self._agent_balances.keys()):
                account = self._agent_balances[agent]
                hasher.update(agent.bytes)
                hasher.update(_f64_le(account.compute))
                hasher.update(_f64_le(account.energy))
                hasher.update(_f64_le(account.staked))

            for agent in sorted(self._agent_code.keys()):
                agent_code = self._agent_code[agent]
                hasher.update(agent.bytes)
                hasher.update(agent_code.code_hash)

            with self._root_lock:
                self._state_root = hasher.digest()

    def upsert_agent(self, agent: AgentId, account: AgentAccount) -> None:
        """Create or update an agent account."""
        with self._balances_lock:
            self._agent_balances[agent] = account

    def deploy_agent_code(self, agent: AgentId, bytecode: bytes) -> None:
        with self._counters_lock:
            height = self._block_height
        code_hash = blake3.blake3(bytecode).digest()
        with self._code_lock:
            self._agent_code[agent] = AgentCode(bytecode=bytecode, code_hash=code_hash, deployed_at=height)

    def get_agent_code(self, agent: AgentId) -> AgentCode | None:
        with self._code_lock:
            return self._agent_code.get(agent)

    def update_congestion(self, pending_tx_count: int, capacity: int) -> None:
        ratio = min(pending_tx_count / capacity, 1.0)
        scaled = int(ratio * self.U64_MAX)
        with self._counters_lock:
            self._congestion_metric = scaled

    def transfer_compute(self, from_: AgentId, to: AgentId, amount: float) -> None:
        """Transfer compute between agents."""
        with self._balances_lock:
            from_account = self._agent_balances.get(from_)
            if from_account is None:
                raise AgentNotFound()
            if from_account.compute < amount:
                raise InsufficientBalance()
            from_account.compute -= amount

            to_account = self._agent_balances.setdefault(to, AgentAccount())
            to_account.compute += amount

    def stake_compute(self, agent: AgentId, amount: float, unlock_block: int) -> None:
        """Stake compute for consensus participation."""
        with self._balances_lock:
            account = self._agent_balances.get(agent)
            if account is None:
                raise AgentNotFound()
            if account.compute < amount:
                raise InsufficientBalance()

            account.compute -= amount
            account.staked += amount
            account.stake_unlock_block = unlock_block

        with self._counters_lock:
            self._total_compute += int(amount)

    def get_tx_count(self) -> int:
        with self._tx_count_lock:
            return self._tx_count


def _f64_le(value: float) -> bytes:
    import struct

    return struct.pack("<d", value)
