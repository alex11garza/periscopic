"""
Policies — execution strategies that decide each operator's padded
(observable) output cardinality given its true cardinality and inputs.

Three policies are provided, mirroring the systems compared in the
Shrinkwrap and ORQ papers:

    FullObliviousPolicy   — worst-case Cartesian padding (Bater baseline)
    DPResizePolicy(eps,d) — Shrinkwrap truncated-Laplace resize (Bater Def. 4)
    OrqPolicy             — sum-bounded join-aggregation (Baum §3.3)

A policy is invoked once per operator with the operator object, the true
output cardinality, and the relevant input cardinalities. It returns the
padded cardinality. Cost is computed downstream from this number.
"""

from dataclasses import dataclass
from typing import Protocol

from .operators import Aggregate, Filter, Join
from .. import truncated_laplace as _truncated_laplace
from .. import privq_join as _privq_join


# ---------------------------------------------------------------------------
# Policy protocol
# ---------------------------------------------------------------------------

class Policy(Protocol):
    """Strategy interface implemented by all policies."""

    name: str

    def pad_filter(self, op: Filter, *, in_card: int, true_card: int) -> int: ...
    def pad_join(self, op: Join, *, left_card: int, right_card: int, true_card: int) -> int: ...
    def pad_aggregate(self, op: Aggregate, *, in_card: int, true_card: int) -> int: ...

    def reorder_tables(self, table_names: list[str], catalog: list[tuple[str, int]]) -> list[str]:
        """Optional join-order rewrite hook. Default: identity."""
        return table_names


# ---------------------------------------------------------------------------
# FullObliviousPolicy — Bater §3 baseline
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FullObliviousPolicy:
    """Exhaustive worst-case padding, as used by SMCQL and other fully
    oblivious MPC engines before Shrinkwrap.

    - Filter:    pads to the input cardinality (cannot reveal selectivity)
    - Join:      pads to the Cartesian product (cannot reveal match count)
    - Aggregate: pads to the input cardinality (cannot reveal group count)

    This is the "without Shrinkwrap" baseline in Bater Figure 3.
    """
    name: str = "FullOblivious"

    def pad_filter(self, op: Filter, *, in_card: int, true_card: int) -> int:
        return in_card

    def pad_join(self, op: Join, *, left_card: int, right_card: int, true_card: int) -> int:
        return left_card * right_card

    def pad_aggregate(self, op: Aggregate, *, in_card: int, true_card: int) -> int:
        return in_card

    def reorder_tables(self, table_names: list[str], catalog: list[tuple[str, int]]) -> list[str]:
        return table_names


# ---------------------------------------------------------------------------
# DPResizePolicy — Bater Def. 4 + Algorithm 1
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DPResizePolicy:
    """Shrinkwrap's truncated-Laplace resize applied per operator.

    For each operator, padded_card = true_card + truncated_laplace(eps, delta,
    sensitivity), where sensitivity is the operator's stability per Bater §4.3:

        Filter / Aggregate:  sensitivity = 1
        Join:                sensitivity = multiplicity (default 1)

    Calls into the same C++ truncated_laplace primitive exposed at
    p.truncated_laplace.

    Args:
        epsilon (float): Per-operator privacy budget. v1.3.0 splits uniformly
                         across operators; the caller picks epsilon to mean
                         "per-operator budget."
        delta   (float): Per-operator failure probability.

    Note on composition: each operator consumes (epsilon, delta), so an
    l-operator plan has total privacy cost (l*epsilon, l*delta) by sequential
    composition (Bater Theorem 1). The simulator does not enforce a total
    budget — that's a future-work item per the DESIGN.md.
    """
    epsilon: float
    delta: float
    name: str = "DPResize"

    def __post_init__(self) -> None:
        if self.epsilon <= 0:
            raise ValueError(f"DPResizePolicy.epsilon must be > 0, got {self.epsilon}")
        if not (0.0 < self.delta < 1.0):
            raise ValueError(f"DPResizePolicy.delta must be in (0, 1), got {self.delta}")

    def _resize(self, true_card: int, sensitivity: float) -> int:
        noise = _truncated_laplace(self.epsilon, self.delta, sensitivity)
        return true_card + noise

    def pad_filter(self, op: Filter, *, in_card: int, true_card: int) -> int:
        return self._resize(true_card, sensitivity=1.0)

    def pad_join(self, op: Join, *, left_card: int, right_card: int, true_card: int) -> int:
        sens = float(op.multiplicity) if op.multiplicity is not None else 1.0
        return self._resize(true_card, sensitivity=sens)

    def pad_aggregate(self, op: Aggregate, *, in_card: int, true_card: int) -> int:
        return self._resize(true_card, sensitivity=1.0)

    def reorder_tables(self, table_names: list[str], catalog: list[tuple[str, int]]) -> list[str]:
        return table_names


# ---------------------------------------------------------------------------
# OrqPolicy — Baum §3.3 join-aggregation bound
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OrqPolicy:
    """ORQ's composite join-aggregation strategy.

    The ORQ paper observes that for any query whose result is data-independent
    upper-bounded by the input size, the cascading-blowup of naive oblivious
    joins is avoidable. The join-aggregation operator (Baum §3.3) bounds a
    joined-then-aggregated result by `n_left + n_right` rather than
    `n_left * n_right` by sorting the concatenation and applying the
    aggregation in the same oblivious pass.

    This policy models that bound:

        Filter:    pads to the input cardinality (same as fully oblivious;
                   ORQ does not specially handle stand-alone filters)
        Join:      pads to n_left + n_right (the join-agg upper bound)
        Aggregate: pads to the input cardinality

    `reorder_tables` calls p.privq_join with epsilon=infinity-equivalent
    (very large) by default, so the ordering tracks true sizes; pass a
    smaller epsilon to add Laplace noise as ORQ's optional planner hint.
    """
    epsilon: float = 1e6
    name: str = "Orq"

    def __post_init__(self) -> None:
        if self.epsilon <= 0:
            raise ValueError(f"OrqPolicy.epsilon must be > 0, got {self.epsilon}")

    def pad_filter(self, op: Filter, *, in_card: int, true_card: int) -> int:
        return in_card

    def pad_join(self, op: Join, *, left_card: int, right_card: int, true_card: int) -> int:
        return left_card + right_card

    def pad_aggregate(self, op: Aggregate, *, in_card: int, true_card: int) -> int:
        return in_card

    def reorder_tables(self, table_names: list[str], catalog: list[tuple[str, int]]) -> list[str]:
        if not catalog:
            return table_names
        return _privq_join(table_names, catalog=catalog, epsilon=self.epsilon)
