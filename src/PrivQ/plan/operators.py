"""
Operators — Filter, Join, Aggregate.

Each operator is a frozen dataclass describing one step in a query plan.
Operators do not execute; they carry the parameters a policy needs to
compute true and padded output cardinalities.

The simulator threads a single "current cardinality" through the chain.
The first operator reads from its named table(s); each subsequent operator
treats the previous step's output as its (left) input.
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class Filter:
    """Row-level predicate over a single input.

    Args:
        table       (str):   Name of the input table (used by the first
                             operator in a chain; ignored if chained after
                             another operator, which produces its input).
        predicate   (str):   Human-readable predicate string. Not executed;
                             only used in reports.
        selectivity (float): Fraction of rows expected to pass. In (0, 1].
                             Caller supplies; the simulator does not estimate.
    """
    table: str
    predicate: str
    selectivity: float = 1.0

    def __post_init__(self) -> None:
        if not (0.0 < self.selectivity <= 1.0):
            raise ValueError(
                f"Filter.selectivity must be in (0, 1], got {self.selectivity}"
            )

    def __str__(self) -> str:
        return f"Filter({self.table}, {self.predicate})"


@dataclass(frozen=True)
class Join:
    """Equi-join of two inputs on a key.

    Args:
        left         (str):           Left input table name (or "" to use the
                                      previous chain step's output).
        right        (str):           Right input table name.
        on           (str):           Join key (informational; not executed).
        multiplicity (Optional[int]): Max rows in the right input sharing one
                                      key value. If given, true output is bounded
                                      by `left * multiplicity` instead of the
                                      Cartesian product. Mirrors the m-stability
                                      notion from Bater et al. §4.3.
    """
    left: str
    right: str
    on: str
    multiplicity: Optional[int] = None

    def __post_init__(self) -> None:
        if self.multiplicity is not None and self.multiplicity < 1:
            raise ValueError(
                f"Join.multiplicity must be >= 1, got {self.multiplicity}"
            )

    def __str__(self) -> str:
        return f"Join({self.left}, {self.right}, on={self.on})"


AggOp = Literal["count", "sum", "distinct"]


@dataclass(frozen=True)
class Aggregate:
    """Group-by aggregation.

    Args:
        group_by   (str):           Grouping key (informational; not executed).
        op         (AggOp):         Aggregation kind: "count", "sum", or "distinct".
        n_groups   (Optional[int]): True number of output groups. If None, defaults
                                    to the input cardinality (worst case: every row
                                    is its own group). Caller supplies for realism.
    """
    group_by: str
    op: AggOp = "count"
    n_groups: Optional[int] = None

    def __post_init__(self) -> None:
        if self.op not in ("count", "sum", "distinct"):
            raise ValueError(
                f"Aggregate.op must be one of count/sum/distinct, got {self.op!r}"
            )
        if self.n_groups is not None and self.n_groups < 0:
            raise ValueError(
                f"Aggregate.n_groups must be >= 0, got {self.n_groups}"
            )

    def __str__(self) -> str:
        return f"Aggregate(group_by={self.group_by}, op={self.op})"
