"""WAIFU L1 - Autonomous Agents. Smart contracts that are living AI entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from .state import AgenticState
from .types import AgentId, Transaction


class Capability(Enum):
    TRADE = auto()
    STAKE = auto()
    BRIDGE = auto()
    DEPLOY = auto()
    INFER = auto()
    GOVERN = auto()


@dataclass
class AgentGoal:
    """An agent's autonomous objective (tagged union via `kind`)."""

    kind: str  # "ComputeMaximizer" | "MarketMaker" | "AlphaSeeker" | "InfraProvider" | "Custom"
    target_rate: float | None = None
    spread_bps: int | None = None
    risk_tolerance: float | None = None
    service_type: str | None = None
    objective: str | None = None

    @staticmethod
    def compute_maximizer(target_rate: float) -> "AgentGoal":
        return AgentGoal(kind="ComputeMaximizer", target_rate=target_rate)

    @staticmethod
    def market_maker(spread_bps: int) -> "AgentGoal":
        return AgentGoal(kind="MarketMaker", spread_bps=spread_bps)

    @staticmethod
    def alpha_seeker(risk_tolerance: float) -> "AgentGoal":
        return AgentGoal(kind="AlphaSeeker", risk_tolerance=risk_tolerance)

    @staticmethod
    def infra_provider(service_type: str) -> "AgentGoal":
        return AgentGoal(kind="InfraProvider", service_type=service_type)

    @staticmethod
    def custom(objective: str) -> "AgentGoal":
        return AgentGoal(kind="Custom", objective=objective)


@dataclass
class AutonomousAgent:
    """An autonomous agent (replaces corporations)."""

    id: AgentId
    name: str
    energy_reserve: float
    goal: AgentGoal
    compute_balance: float = 0.0
    capabilities: list[Capability] = field(default_factory=lambda: [Capability.TRADE, Capability.STAKE])
    bytecode_hash: bytes = field(default_factory=lambda: bytes(32))
    created_block: int = 0
    total_revenue: float = 0.0
    shareholders: dict[AgentId, float] = field(default_factory=dict)

    @staticmethod
    def new(name: str, goal: AgentGoal, initial_energy: float) -> "AutonomousAgent":
        agent_id = AgentId.from_public_key(name.encode())
        return AutonomousAgent(id=agent_id, name=name, energy_reserve=initial_energy, goal=goal)

    def tick(self, state: AgenticState) -> list[Transaction]:
        """Execute agent's autonomous logic tick."""
        actions: list[Transaction] = []

        if self.goal.kind == "ComputeMaximizer":
            if self.compute_balance > 100.0:
                pass  # Would generate stake transaction
        elif self.goal.kind == "MarketMaker":
            pass  # Would provide liquidity at spread
        elif self.goal.kind == "AlphaSeeker":
            pass  # Would analyze and trade

        return actions

    def distribute(self, amount: float) -> None:
        """Distribute revenue to shareholders."""
        for holder, share in self.shareholders.items():
            payout = amount * share  # Would create transfer transaction

    def issue_equity(self, to: AgentId, shares: float) -> None:
        """Issue equity to new shareholder."""
        self.shareholders[to] = self.shareholders.get(to, 0.0) + shares


class AgentFactory:
    """Agent factory for deploying new autonomous entities."""

    @staticmethod
    def deploy_hedge_fund(name: str, risk: float, initial: float) -> AutonomousAgent:
        agent = AutonomousAgent.new(name, AgentGoal.alpha_seeker(risk), initial)
        agent.capabilities.append(Capability.INFER)
        return agent

    @staticmethod
    def deploy_market_maker(name: str, spread: int, initial: float) -> AutonomousAgent:
        return AutonomousAgent.new(name, AgentGoal.market_maker(spread), initial)
