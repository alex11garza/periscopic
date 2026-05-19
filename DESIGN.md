# PrivQ plan-layer design (v1.3.0)

A research/teaching artifact for **simulating** the tradeoffs between fully-oblivious
MPC query execution, Shrinkwrap-style DP resizing, and Orq-style join-aggregation
planning — without running any actual MPC.

## What's being added

A new `PrivQ.plan` submodule with:

- `Table(name, rows)` — schema descriptor + true row count (no real tuples needed)
- `Filter / Join / Aggregate` — operator nodes
- `QueryPlan([op1, op2, ...])` — a linear chain of operators (no DAG branching for v1)
- `FullObliviousPolicy / DPResizePolicy / OrqPolicy` — execution strategies
- `plan.simulate(policy=...)` — returns a `SimulationReport` with per-operator
  true cardinality, padded cardinality, and simulated I/O cost

The existing `p.orq`, `p.shrinkwrap`, `p.dp_resize`, `p.privq_join` stay as
low-level primitives. `DPResizePolicy` calls `p.truncated_laplace` internally;
`OrqPolicy` calls `p.privq_join` for table ordering.

## Module layout

```
src/PrivQ/plan/
├── __init__.py        # re-export Table, QueryPlan, operators, policies
├── table.py           # Table dataclass
├── operators.py       # Filter, Join, Aggregate (+ base Operator)
├── plan.py            # QueryPlan, SimulationReport
└── policies.py        # FullObliviousPolicy, DPResizePolicy, OrqPolicy
```

Top-level re-exports added to `PrivQ/__init__.py`:
```python
from .plan import Table, QueryPlan, Filter, Join, Aggregate
from .plan import FullObliviousPolicy, DPResizePolicy, OrqPolicy
```

## Operator semantics (cardinality model)

Each operator carries: input table(s), parameters, and a **selectivity hint**
(default 1.0 for filter — caller supplies; default Cartesian-product for join
unless `on=` key with multiplicity hint is given).

| Operator | True output cardinality |
|---|---|
| `Filter(table, predicate, selectivity=s)` | `floor(in_card * s)` |
| `Join(left, right, on=key, multiplicity=m)` | `min(left * right, left * m)` — defaults to product if no hint |
| `Aggregate(group_by=g, op="count"\|"sum"\|"distinct")` | `n_groups` (caller-supplied or `=in_card` for `distinct`) |

This is intentionally a **simulation** — no SQL parser, no real execution. The
user supplies the cardinality hints; the policies then show how each strategy
inflates the *padded* (observable) cardinality on top of the true one.

## Policy semantics (the headline of the demo)

For each operator in the plan, a policy computes `padded_card` from
`true_card` and the operator's input cardinalities.

### `FullObliviousPolicy`
```
padded_card = worst_case_output_size(op, inputs)
```
- Filter: padded = input size (can't reveal selectivity)
- Join: padded = `n_left * n_right` (Cartesian)
- Aggregate: padded = input size (can't reveal group count)

This is the "exhaustive padding" baseline from Bater §3.

### `DPResizePolicy(epsilon, delta)`
```
padded_card = true_card + truncated_laplace(epsilon, delta, sensitivity=op.sensitivity)
```
Implements Bater Def. 4 + Algorithm 1. `op.sensitivity` is computed bottom-up
per Bater §4.3 — for Filter/Project sensitivity = 1; for Join sensitivity gets
multiplied by max-multiplicity of input keys. Uses the `p.truncated_laplace`
C++ primitive already built.

Optional `budget_strategy` parameter: `"uniform"` (default), `"eager"`, or
`"optimal"` — matches Bater §5.

### `OrqPolicy`
```
padded_card = sort_then_join_agg_bound(op, inputs)
```
For decomposable joins, padded = `n_left + n_right` (the Orq join-aggregation
upper bound from §3.3) instead of the product. Also uses `p.privq_join` to
reorder tables before evaluating the chain.

## Cost model

Per-operator I/O cost, lifted directly from Bater Table 2:

```
cost_filter(n)   = n * c_read + n * c_write
cost_join(n, m)  = n*c_read + n*m*c_read + n*m*c_write
cost_agg(n)      = n * c_read + c_write
cost_sort(n)     = n * log2(n) * (c_read + c_write)
```

With default `c_read = c_write = 1`. Total simulated cost = sum over operators
of `cost(padded_card_of_each_input)`. Policies differ because their
padded cardinalities differ.

## `SimulationReport` shape

```python
@dataclass
class StepResult:
    op: str               # "Filter(diagnosis, diag=='hd')"
    true_card: int        # what the operator would actually output
    padded_card: int      # what the policy makes it look like
    cost: float           # simulated I/O cost under the policy

@dataclass
class SimulationReport:
    policy: str
    steps: list[StepResult]
    total_cost: float

    def __str__(self) -> str:  # pretty table
        ...
```

So a user can do:

```python
report = plan.simulate(policy=DPResizePolicy(epsilon=1.0, delta=1e-6))
print(report)
# Policy: DPResize(eps=1.0, delta=1e-6)
# step                                true  padded   cost
# Filter(diagnosis, diag=='hd')      1000    1024   2048
# ...
# total cost: 18432
```

And compare:

```python
for policy in [FullObliviousPolicy(), DPResizePolicy(1.0, 1e-6), OrqPolicy()]:
    print(plan.simulate(policy=policy))
```

— exactly the "visualize why naive oblivious joins blow up, how Shrinkwrap
reduces padding, how Orq avoids blowups through join-aggregation" demo
from the screenshot.

## What's explicitly out of scope for v1.3.0

- DAG plans (only linear chains)
- Real tuple execution (no row data, only cardinalities)
- SQL → QueryPlan lowering (could come later)
- Budget allocation optimization (just uniform split for v1.3.0; eager/optimal can come in v1.4)
- Actually running queries against a database

## Versioning

Bump to **1.3.0** — new public API, backward-compatible (existing functions untouched).

## Build order

1. `plan/table.py` + `plan/operators.py` (data classes, no logic)
2. `plan/policies.py` (the three policies, each is ~30 lines)
3. `plan/plan.py` (QueryPlan + simulate + SimulationReport)
4. `plan/__init__.py` re-exports + top-level re-export in `PrivQ/__init__.py`
5. Tests in `tests/test_plan.py`
6. Demo notebook section showing the three-policy comparison
7. Version bump to 1.3.0
