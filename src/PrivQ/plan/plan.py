"""
QueryPlan — a linear chain of operators evaluated under a policy.

The simulator threads a single "current cardinality" through the chain:

    step 0   reads from its named input table(s)
    step k   uses step (k-1)'s output as its left/only input

Per step, the policy decides the *padded* (observable) output cardinality
from the true one. The cost model then converts those padded cardinalities
into a simulated I/O cost (Bater et al. Table 2).

No tuples are materialized. This is a pencil-and-paper simulator that lets
you compare fully-oblivious, DP-resize, and ORQ planning strategies side
by side without standing up an MPC stack.
"""

from dataclasses import dataclass, field
from math import log2
from typing import Optional

from .operators import Aggregate, Filter, Join
from .policies import FullObliviousPolicy, Policy
from .table import Table


# ---------------------------------------------------------------------------
# Cost model — Bater et al. Table 2
# ---------------------------------------------------------------------------
#
# Lifted directly from the Shrinkwrap cost model. We use unit read/write
# costs (c_read = c_write = 1) so reported numbers are comparable across
# policies on the same plan. A future patch can plumb protocol-specific
# constants through if we want absolute timings.

_C_READ  = 1.0
_C_WRITE = 1.0


def _cost_filter(n: int) -> float:
    return n * _C_READ + n * _C_WRITE


def _cost_join(n: int, m: int) -> float:
    return n * _C_READ + n * m * _C_READ + n * m * _C_WRITE


def _cost_aggregate(n: int) -> float:
    return n * _C_READ + _C_WRITE


def _cost_sort(n: int) -> float:
    if n <= 1:
        return 0.0
    return n * log2(n) * (_C_READ + _C_WRITE)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """One operator's outcome under a policy."""
    op:          str
    true_card:   int
    padded_card: int
    cost:        float


@dataclass
class SimulationReport:
    """The complete result of a simulate() call."""
    policy:     str
    table_order: list[str]
    steps:      list[StepResult] = field(default_factory=list)
    total_cost: float = 0.0

    def __str__(self) -> str:
        header = f"Policy: {self.policy}\nTable order: {self.table_order}\n"
        if not self.steps:
            return header + "(no steps)\n"

        # Column widths sized to content
        op_w     = max(len("step"),    max(len(s.op)                  for s in self.steps))
        true_w   = max(len("true"),    max(len(f"{s.true_card:,}")    for s in self.steps))
        padded_w = max(len("padded"),  max(len(f"{s.padded_card:,}")  for s in self.steps))
        cost_w   = max(len("cost"),    max(len(f"{s.cost:,.0f}")      for s in self.steps))

        lines = [
            header,
            f"  {'step':<{op_w}}  {'true':>{true_w}}  {'padded':>{padded_w}}  {'cost':>{cost_w}}",
            f"  {'-' * op_w}  {'-' * true_w}  {'-' * padded_w}  {'-' * cost_w}",
        ]
        for s in self.steps:
            lines.append(
                f"  {s.op:<{op_w}}  {s.true_card:>{true_w},}  "
                f"{s.padded_card:>{padded_w},}  {s.cost:>{cost_w},.0f}"
            )
        lines.append(f"\n  total cost: {self.total_cost:,.0f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# QueryPlan
# ---------------------------------------------------------------------------

Operator = Filter | Join | Aggregate


class QueryPlan:
    """A linear chain of relational operators to simulate under a policy.

    Args:
        ops (list[Operator]): Operators in evaluation order. The first
                              operator reads from its named table(s); each
                              subsequent operator's left input is the previous
                              step's output.

    Example:
        >>> from PrivQ.plan import QueryPlan, Table, Filter, Join, Aggregate
        >>> from PrivQ.plan import FullObliviousPolicy, DPResizePolicy
        >>>
        >>> plan = QueryPlan([
        ...     Filter("diagnosis", predicate="diag == 'hd'", selectivity=0.01),
        ...     Join("",            "medication",  on="code", multiplicity=3),
        ...     Join("",            "demographic", on="pid",  multiplicity=1),
        ...     Aggregate(group_by="pid", op="distinct"),
        ... ])
        >>> tables = [
        ...     Table("diagnosis",   rows=10_000),
        ...     Table("medication",  rows=20_000),
        ...     Table("demographic", rows= 5_000),
        ... ]
        >>> report = plan.simulate(tables=tables, policy=FullObliviousPolicy())
        >>> print(report)  # doctest: +SKIP
    """

    def __init__(self, ops: list[Operator]) -> None:
        if not ops:
            raise ValueError("QueryPlan requires at least one operator")
        self.ops = list(ops)

    # ---------------------------------------------------------------------
    # True-cardinality model
    # ---------------------------------------------------------------------
    # These are intentionally simple — the user supplies selectivities and
    # multiplicities on the operators, and we propagate them. They model
    # what the operator *would* output under faithful (non-padded) execution.

    @staticmethod
    def _true_filter(op: Filter, in_card: int) -> int:
        return int(in_card * op.selectivity)

    @staticmethod
    def _true_join(op: Join, left_card: int, right_card: int) -> int:
        if op.multiplicity is not None:
            return min(left_card * right_card, left_card * op.multiplicity)
        return left_card * right_card

    @staticmethod
    def _true_aggregate(op: Aggregate, in_card: int) -> int:
        if op.n_groups is not None:
            return op.n_groups
        # distinct conservatively keeps all rows; count/sum collapse to 1 group
        # per unspecified group_by, but without a hint we assume worst case.
        return in_card if op.op == "distinct" else in_card

    # ---------------------------------------------------------------------
    # Simulate
    # ---------------------------------------------------------------------

    def simulate(
        self,
        *,
        tables: list[Table],
        policy: Optional[Policy] = None,
    ) -> SimulationReport:
        """Run the plan under `policy` and return per-step + total results.

        Args:
            tables (list[Table]): Tables referenced by the plan's operators.
                                  Names must match operator `table` / `right`
                                  / `left` fields.
            policy (Policy):      Padding strategy. Defaults to FullObliviousPolicy.
        """
        if policy is None:
            policy = FullObliviousPolicy()

        by_name = {t.name: t for t in tables}
        # Hand the policy the chance to reorder a table-name list. v1.3.0
        # uses this only for OrqPolicy and only as a reported field; we do
        # not actually reorder the operator chain (a future-work item).
        catalog = [(t.name, t.rows) for t in tables]
        table_order = policy.reorder_tables([t.name for t in tables], catalog)

        report = SimulationReport(policy=policy.name, table_order=table_order)

        current_true: int = 0
        current_padded: int = 0

        for i, op in enumerate(self.ops):
            if isinstance(op, Filter):
                if i == 0:
                    if op.table not in by_name:
                        raise KeyError(f"Filter references unknown table {op.table!r}")
                    in_true   = by_name[op.table].rows
                    in_padded = by_name[op.table].rows
                else:
                    in_true   = current_true
                    in_padded = current_padded

                true_out   = self._true_filter(op, in_true)
                padded_out = policy.pad_filter(op, in_card=in_padded, true_card=true_out)
                cost       = _cost_filter(in_padded)

            elif isinstance(op, Join):
                # Left input: either a named table (first op or explicit), or
                # the chain's current cardinality.
                if i == 0 or op.left:
                    if op.left not in by_name:
                        raise KeyError(f"Join references unknown left table {op.left!r}")
                    left_true   = by_name[op.left].rows
                    left_padded = by_name[op.left].rows
                else:
                    left_true   = current_true
                    left_padded = current_padded

                if op.right not in by_name:
                    raise KeyError(f"Join references unknown right table {op.right!r}")
                right_true   = by_name[op.right].rows
                right_padded = by_name[op.right].rows

                true_out   = self._true_join(op, left_true, right_true)
                padded_out = policy.pad_join(
                    op,
                    left_card=left_padded,
                    right_card=right_padded,
                    true_card=true_out,
                )
                cost = _cost_join(left_padded, right_padded)

            elif isinstance(op, Aggregate):
                if i == 0:
                    raise ValueError("Aggregate cannot be the first operator (nothing to aggregate)")
                in_true   = current_true
                in_padded = current_padded

                true_out   = self._true_aggregate(op, in_true)
                padded_out = policy.pad_aggregate(op, in_card=in_padded, true_card=true_out)
                # Aggregation requires a sort (per Bater Table 2 ordering)
                cost = _cost_sort(in_padded) + _cost_aggregate(in_padded)

            else:  # pragma: no cover — exhaustive over the Operator union
                raise TypeError(f"Unknown operator type: {type(op).__name__}")

            current_true   = true_out
            current_padded = padded_out
            report.steps.append(
                StepResult(op=str(op), true_card=true_out, padded_card=padded_out, cost=cost)
            )
            report.total_cost += cost

        return report
