"""WAIFU L1 - The Base Physics. All fundamental types for the Agentic Economy."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Union

import blake3


class AgentId:
    """Unique identifier for an Agentic Entity (not a human wallet)."""

    __slots__ = ("bytes",)

    def __init__(self, raw: bytes):
        if len(raw) != 32:
            raise ValueError("AgentId must be exactly 32 bytes")
        self.bytes = raw

    @staticmethod
    def from_public_key(pk: bytes) -> "AgentId":
        return AgentId(blake3.blake3(pk).digest())

    @staticmethod
    def genesis() -> "AgentId":
        return AgentId(bytes(32))

    def to_hex(self) -> str:
        return self.bytes.hex()

    def __str__(self) -> str:
        return self.to_hex()[:16]

    def __repr__(self) -> str:
        return f"AgentId({self.to_hex()})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AgentId) and self.bytes == other.bytes

    def __hash__(self) -> int:
        return hash(self.bytes)

    def __lt__(self, other: "AgentId") -> bool:
        return self.bytes < other.bytes

    def to_json(self):
        return list(self.bytes)


class Priority(IntEnum):
    """Priority levels for transaction processing."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Operation:
    """Types of operations in the Agentic Economy (tagged union via `kind`)."""

    kind: str  # "Transfer" | "Execute" | "Deploy" | "Bridge" | "Stake" | "Infer" | "Swap"
    amount: Optional[float] = None
    function: Optional[str] = None
    args: bytes = b""
    bytecode: bytes = b""
    initial_energy: Optional[float] = None
    source_chain: Optional[str] = None
    proof: bytes = b""
    prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    input_asset: Optional["SovereignAsset"] = None
    output_asset_type: Optional["AssetType"] = None

    @staticmethod
    def transfer(amount: float) -> "Operation":
        return Operation(kind="Transfer", amount=amount)

    @staticmethod
    def execute(function: str, args: bytes = b"") -> "Operation":
        return Operation(kind="Execute", function=function, args=args)

    @staticmethod
    def deploy(bytecode: bytes, initial_energy: float) -> "Operation":
        return Operation(kind="Deploy", bytecode=bytecode, initial_energy=initial_energy)

    @staticmethod
    def bridge(source_chain: str, proof: bytes) -> "Operation":
        return Operation(kind="Bridge", source_chain=source_chain, proof=proof)

    @staticmethod
    def stake(amount: float) -> "Operation":
        return Operation(kind="Stake", amount=amount)

    @staticmethod
    def infer(prompt: str, max_tokens: int) -> "Operation":
        return Operation(kind="Infer", prompt=prompt, max_tokens=max_tokens)

    @staticmethod
    def swap(input_asset: "SovereignAsset", output_asset_type: "AssetType") -> "Operation":
        return Operation(kind="Swap", input_asset=input_asset, output_asset_type=output_asset_type)


@dataclass
class TransactionContext:
    """The semantic context that the LLM uses to determine pricing."""

    operation: Operation
    energy_budget: float
    priority: Priority
    payload: bytes = b""
    oracle_refs: list[str] = field(default_factory=list)


@dataclass
class Transaction:
    """The raw transaction submitted to the mempool.

    NOTE: No explicit price. The LLM determines the clearing rate.
    """

    from_: AgentId
    to: AgentId
    context: TransactionContext
    signature: bytes = field(default_factory=lambda: bytes(64))
    nonce: int = 0
    timestamp: int = field(default_factory=lambda: time.time_ns())

    @staticmethod
    def new(from_: AgentId, to: AgentId, context: TransactionContext) -> "Transaction":
        return Transaction(from_=from_, to=to, context=context)

    def _to_json_dict(self) -> dict:
        op = self.context.operation
        return {
            "from": self.from_.to_json(),
            "to": self.to.to_json(),
            "context": {
                "operation": {"kind": op.kind, "amount": op.amount, "function": op.function,
                              "args": list(op.args), "bytecode": list(op.bytecode),
                              "initial_energy": op.initial_energy, "source_chain": op.source_chain,
                              "proof": list(op.proof), "prompt": op.prompt, "max_tokens": op.max_tokens},
                "energy_budget": self.context.energy_budget,
                "priority": int(self.context.priority),
                "payload": list(self.context.payload),
                "oracle_refs": self.context.oracle_refs,
            },
            "signature": list(self.signature),
            "nonce": self.nonce,
            "timestamp": self.timestamp,
        }

    def hash(self) -> bytes:
        """Compute the transaction hash (used for DAG linking)."""
        serialized = json.dumps(self._to_json_dict(), sort_keys=True).encode()
        return blake3.blake3(serialized).digest()


@dataclass
class StakedCompute:
    amount: float
    unlock_block: int


@dataclass
class LegacyBridged:
    source_chain: str
    original_asset: str
    amount: float
    conversion_rate: float


@dataclass
class AgentEquity:
    agent_id: AgentId
    shares: float


SovereignAsset = Union[float, StakedCompute, "Energy", LegacyBridged, AgentEquity]
"""Sovereign assets in the WAIFU economy. There are no "tokens" -- only compute and derivatives.

Represented as a tagged value rather than a Rust-style enum: use the
`Compute`/`Energy`/... constructor helpers below instead of raw values.
"""


@dataclass
class Compute:
    amount: float


@dataclass
class Energy:
    amount: float


class AssetTypeKind(IntEnum):
    COMPUTE = 0
    ENERGY = 1
    STAKED_COMPUTE = 2
    AGENT_EQUITY = 3


@dataclass
class AssetType:
    """Asset type identifiers for swap operations."""

    kind: AssetTypeKind
    agent_id: Optional[AgentId] = None

    @staticmethod
    def agent_equity(agent_id: AgentId) -> "AssetType":
        return AssetType(kind=AssetTypeKind.AGENT_EQUITY, agent_id=agent_id)


@dataclass
class StateChange:
    agent_id: AgentId
    field: str
    old_value: bytes
    new_value: bytes


@dataclass
class ExecutionResult:
    """Result of transaction execution."""

    success: bool
    gas_used: float
    state_changes: list[StateChange] = field(default_factory=list)
    reason: str = ""

    @staticmethod
    def success_result(gas_used: float, state_changes: Optional[list[StateChange]] = None) -> "ExecutionResult":
        return ExecutionResult(success=True, gas_used=gas_used, state_changes=state_changes or [])

    @staticmethod
    def failure(reason: str, gas_used: float) -> "ExecutionResult":
        return ExecutionResult(success=False, gas_used=gas_used, reason=reason)


@dataclass
class PricedTransaction:
    """A transaction that has been priced by the LLM."""

    original: Transaction
    clearing_rate: float
    pricing_rationale: str
    result: ExecutionResult


@dataclass
class PoIProof:
    """Proof-of-Intelligence validation proof."""

    model_hash: bytes
    input_hash: bytes
    output_hash: bytes
    temperature: float
    signature: bytes = field(default_factory=lambda: bytes(64))

    def is_deterministic(self) -> bool:
        return self.temperature == 0.0


@dataclass
class Block:
    """A validated block in the WAIFU DAG."""

    height: int
    hash: bytes
    parents: list[bytes]
    transactions: list[PricedTransaction]
    llm_state_root: bytes
    validator: AgentId
    poi_proof: PoIProof
    timestamp: int

    def compute_hash(self) -> bytes:
        """Compute the block hash from its contents."""
        hasher = blake3.blake3()
        hasher.update(self.height.to_bytes(8, "little"))
        for parent in self.parents:
            hasher.update(parent)
        for tx in self.transactions:
            hasher.update(tx.original.hash())
        hasher.update(self.llm_state_root)
        hasher.update(self.validator.bytes)
        return hasher.digest()


@dataclass
class NetworkMessage:
    """Network messages for the mesh (tagged union via `kind`)."""

    kind: str
    transaction: Optional[Transaction] = None
    block: Optional[Block] = None
    block_hash: Optional[bytes] = None
    blocks: list[Block] = field(default_factory=list)
    agent_id: Optional[AgentId] = None
    capabilities: list[str] = field(default_factory=list)
    from_height: Optional[int] = None
    timestamp: Optional[int] = None
