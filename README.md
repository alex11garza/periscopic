# PrivQ

**PrivQ** is a privacy-preserving SQL transformation library and a teaching
simulator for the privacy/performance tradeoffs studied in two recent systems
papers — [ORQ (Baum et al., SOSP 2025)](https://arxiv.org/abs/2509.10793)
and [Shrinkwrap (Bater et al., VLDB 2018)](https://arxiv.org/abs/1810.01816).

PrivQ ships two layers:

1. A **SQL-text rewriting layer** — sort `SELECT` columns, apply structural
   padding to obscure query shape, append a differentially-private `LIMIT`,
   and noise the join order using `Laplace(1/ε)` table-size estimates.
2. A **plan-layer simulator** — build a chain of relational operators and run
   it under three padding policies (fully oblivious, Shrinkwrap DP resize, ORQ
   join-aggregation) to see how each affects intermediate cardinalities and
   simulated I/O cost. No MPC stack required.

It is the artifact for an applied-cybersecurity master's project at Tufts.

---

## Install

```bash
pip install PrivQ
```

Requires Python ≥ 3.9. C++ extensions build automatically via pybind11.

---

## Quick start

```python
import PrivQ as p

sql = "SELECT salary, name, age FROM employees"

# 1. Sort SELECT columns to normalize column-order leakage
sorted_sql = p.orq(sql)
# → "SELECT age, name, salary FROM employees"

# 2. Apply structural padding to obscure query shape
padded_sql = p.shrinkwrap(sorted_sql, padding=True, pad_level=2)

# 3. DP-noisy join order from a catalog
ordered = p.privq_join(
    ["orders", "users", "products"],
    catalog=[("users", 100), ("orders", 200), ("products", 50)],
    epsilon=0.5,
)
# → ['products', 'users', 'orders']  (noised smallest→largest)

# 4. Append a DP LIMIT (Bater Shrinkwrap Def. 4 / Algorithm 1)
limited_sql = p.dp_resize(sql, true_count=100, epsilon=1.0, delta=1e-6)
# → "SELECT salary, name, age FROM employees LIMIT 112"
```

---

## SQL-text API

### `orq(sql)` — column-order normalization

Sorts the `SELECT` column list alphabetically (case-insensitive, original
casing preserved). Conservative — `SELECT *`, single columns, and non-SELECT
statements pass through unchanged.

```python
>>> p.orq("SELECT salary, name, age FROM employees")
'SELECT age, name, salary FROM employees'

>>> p.orq("SELECT Salary, name, Age FROM employees")
'Select Age, name, Salary FROM employees'

>>> p.orq("INSERT INTO employees (name) VALUES ('Alice')")
"INSERT INTO employees (name) VALUES ('Alice')"
```

### `shrinkwrap(sql, padding=True, pad_level=2)` — structural padding

Adds dummy syntactic elements so two queries with different shapes look
more alike on the wire.

| Level | What gets added |
|:----:|:----------------|
| `1` | Comment wrapper only |
| `2` | + column, aggregate, CTE, `ORDER BY`, subquery pads (default) |
| `3` | + dummy `LEFT JOIN` |

```python
>>> print(p.shrinkwrap("SELECT * FROM users", pad_level=2))
    -- shrinkwrap padding
    SELECT *, /* shrinkwrap */ 1 as pad_col /* end */ FROM users
    -- end padding
```

For fine-grained control, `shrinkwrap_pad(sql, name)` applies one named pad
(`query`, `column`, `aggregate`, `cte`, `join`, `orderby`, `subquery`,
`insert`, `update`, `delete`).

### `privq_join(tables, catalog, epsilon=0.5)` — DP join reorder

Reorders tables smallest → largest using `Laplace(1/ε)` noise on the true
catalog row counts. True counts never leave the constructor.

```python
>>> p.privq_join(
...     ["big", "small", "medium"],
...     catalog=[("big", 10_000), ("small", 1), ("medium", 500)],
...     epsilon=1000.0,   # high ε → ordering tracks true sizes
... )
['small', 'medium', 'big']
```

Reuse an estimator across many queries:

```python
est = p.estimator([("users", 100), ("orders", 200)], epsilon=0.5)
est.join_order(["orders", "users"])           # ['users', 'orders']
est.join_order(["users", "unknown_table"])    # unknown tables sort last
```

### `dp_resize(sql, true_count, *, epsilon, delta, sensitivity=1.0)`

Appends (or replaces) a `LIMIT` clause with
`true_count + truncated_laplace(ε, δ, Δ)` — implementing the Resize step
from Bater et al. Algorithm 1 at the SQL-text layer.

```python
>>> p.dp_resize("SELECT name FROM users", 100, epsilon=1.0, delta=1e-5)
'SELECT name FROM users LIMIT 112'      # exact value is random

>>> p.dp_resize("SELECT name FROM users LIMIT 5", 100, epsilon=1.0, delta=1e-5)
'SELECT name FROM users LIMIT 111'      # existing LIMIT is replaced

>>> p.dp_resize("SELECT name FROM users;", 100, epsilon=1.0, delta=1e-5)
'SELECT name FROM users LIMIT 110;'     # trailing semicolons preserved
```

The truncated-Laplace mechanism guarantees `Pr[noise < Δ] ≤ δ`, so the
released LIMIT almost certainly exceeds the true count — no real rows are
dropped.

### `transform(sql, ...)` — full pipeline

Runs all three text-layer stages and returns a dict with each stage's output:

```python
>>> p.transform(
...     "SELECT salary, name FROM orders JOIN users ON orders.user_id = users.id",
...     catalog=[("users", 100), ("orders", 200)],
...     epsilon=0.5,
...     padding=True,
...     pad_level=2,
... )
{
  'original':   '...',
  'orq':        'SELECT name, salary FROM orders JOIN users ON ...',
  'join_order': ['users', 'orders'],
  'shrinkwrap': '... SELECT name, salary ... -- end padding',
}
```

The library returns `join_order` as data; the caller (an upstream layer with
a real SQL parser) is expected to apply it.

### Low-level DP primitives

| Function | Returns |
|---|---|
| `p.laplace_sample(scale)` | `\|X\|` for `X ~ Laplace(0, scale)` |
| `p.noisy_count(n, ε, sensitivity=1.0)` | `max(0, round(n + Lap(sens/ε)))` |
| `p.truncated_laplace(ε, δ, sens=1.0)` | Bater Def. 4 truncated Laplace |

---

## Plan-layer simulator

The text API above tells you *what* to rewrite. The plan layer tells you
*why* — by simulating the same query plan under three different MPC
strategies and showing how each one inflates intermediate cardinalities.

```python
from PrivQ.plan import (
    Table, QueryPlan, Filter, Join, Aggregate,
    FullObliviousPolicy, DPResizePolicy, OrqPolicy,
)

plan = QueryPlan([
    Filter("diagnosis",  predicate="diag == 'hd'", selectivity=0.01),
    Join("",             "medication",  on="code", multiplicity=3),
    Join("",             "demographic", on="pid",  multiplicity=1),
    Aggregate(group_by="pid", op="distinct"),
])

tables = [
    Table("diagnosis",   rows=10_000),
    Table("medication",  rows=20_000),
    Table("demographic", rows= 5_000),
]

for policy in [
    FullObliviousPolicy(),
    DPResizePolicy(epsilon=1.0, delta=1e-6),
    OrqPolicy(),
]:
    print(plan.simulate(tables=tables, policy=policy))
    print()
```

### Output

```
Policy: FullOblivious
Table order: ['diagnosis', 'medication', 'demographic']

  step                                  true             padded                cost
  ------------------------------------  ----  -----------------  ------------------
  Filter(diagnosis, diag == 'hd')        100             10,000              20,000
  Join(, medication, on=code)            300        200,000,000         400,010,000
  Join(, demographic, on=pid)            300  1,000,000,000,000   2,000,200,000,000
  Aggregate(group_by=pid, op=distinct)   300  1,000,000,000,000  80,726,274,277,298

  total cost: 82,726,874,307,298

Policy: DPResize
Table order: ['diagnosis', 'medication', 'demographic']

  step                                  true  padded       cost
  ------------------------------------  ----  ------  ---------
  Filter(diagnosis, diag == 'hd')        100     112     20,000
  Join(, medication, on=code)            300     345  4,480,112
  Join(, demographic, on=pid)            300     316  3,450,345
  Aggregate(group_by=pid, op=distinct)   300     313      5,565

  total cost: 7,956,022

Policy: Orq
Table order: ['demographic', 'diagnosis', 'medication']

  step                                  true  padded         cost
  ------------------------------------  ----  ------  -----------
  Filter(diagnosis, diag == 'hd')        100  10,000       20,000
  Join(, medication, on=code)            300  30,000  400,010,000
  Join(, demographic, on=pid)            300  35,000  300,030,000
  Aggregate(group_by=pid, op=distinct)   300  35,000    1,091,656

  total cost: 701,151,656
```

### Headline numbers

| Policy | Total cost | Speedup vs baseline |
|---|---:|---:|
| `FullObliviousPolicy` | 82,726,874,307,298 | 1× |
| **`DPResizePolicy(ε=1, δ=1e-6)`** | **7,956,022** | **~10,400,000×** |
| `OrqPolicy` | 701,151,656 | ~118,000× |

All three reach the same **true** cardinalities (those depend only on the
data) but radically different **padded** ones. Cost scales with the padded
cardinality, so Cartesian-pad joins are catastrophic and the two principled
strategies dramatically reduce overhead.

### Scaling the input

The cascading-blowup story is even sharper as the base table grows:

| Input rows | FullOblivious | DPResize | Orq |
|---:|---:|---:|---:|
| 1,000 | 6.3 × 10¹⁰ | 1.7 × 10⁵ | 7.1 × 10⁶ |
| 10,000 | 8.3 × 10¹³ | 8.0 × 10⁶ | 7.0 × 10⁸ |
| 50,000 | 1.2 × 10¹⁶ | 1.8 × 10⁸ | 1.8 × 10¹⁰ |

Same plan; same policies; just bigger inputs. FullOblivious grows as
`O(n³)`; DPResize stays roughly linear in the noised cardinalities.

### Sweeping ε — the DP privacy/cost tradeoff

Lower ε ⇒ more privacy per release ⇒ more noise ⇒ more padding ⇒ higher
cost:

| ε | Avg total cost (20 runs) |
|---:|---:|
| 0.01 | 100,107,299 |
| 0.10 | 16,162,952 |
| 0.50 | 8,918,789 |
| 1.00 | 7,976,465 |
| 5.00 | 7,251,214 |

### Policies

| Policy | Filter | Join | Aggregate |
|---|---|---|---|
| `FullObliviousPolicy` | pad to input | pad to n·m | pad to input |
| `DPResizePolicy(ε, δ)` | true + TLap(ε, δ, 1) | true + TLap(ε, δ, m) | true + TLap(ε, δ, 1) |
| `OrqPolicy` | pad to input | pad to n+m | pad to input |

`DPResizePolicy` calls the same C++ `truncated_laplace` primitive used by
`p.dp_resize`; `OrqPolicy.reorder_tables` calls `p.privq_join`.

---

## End-to-end teaching example

The plan-layer simulator tells you *which* operator outputs explode and
*how big* each padded cardinality is. The SQL layer lets you act on that
by emitting a DP-noised `LIMIT` for any operator that hits real SQL.

```python
import PrivQ as p
from PrivQ.plan import (
    Table, QueryPlan, Filter, FullObliviousPolicy, DPResizePolicy,
)

# 1. Simulate the plan
plan = QueryPlan([Filter("diagnosis", predicate="diag = 'hd'", selectivity=0.01)])
tables = [Table("diagnosis", rows=10_000)]

baseline = plan.simulate(tables=tables, policy=FullObliviousPolicy())
dp       = plan.simulate(tables=tables, policy=DPResizePolicy(1.0, 1e-6))

print(f"Full-oblivious would pad to {baseline.steps[-1].padded_card:,} rows")
print(f"DP resize pads to roughly  {dp.steps[-1].padded_card:,} rows")
# Full-oblivious would pad to 10,000 rows
# DP resize pads to roughly      113 rows

# 2. Use the same DP machinery to emit a noised LIMIT for the federated engine
sql = "SELECT pid FROM diagnosis WHERE diag = 'hd'"
true_count = baseline.steps[-1].true_card     # 100
print(p.dp_resize(sql, true_count, epsilon=1.0, delta=1e-6))
# SELECT pid FROM diagnosis WHERE diag = 'hd' LIMIT 112
```

A runnable Jupyter walkthrough of every API is in
[`examples/PrivQ_demo.ipynb`](examples/PrivQ_demo.ipynb).

---

## Honest scope

PrivQ is intended as a **teaching artifact and SQL-rewriting frontend** for
the ORQ + Shrinkwrap line of work. It is *not* a cryptographic MPC engine
and does *not* execute queries obliviously over secret-shared data. Three
things to keep in mind:

- **ShrinkWrap's `shrinkwrap()` padding is syntactic** — it obscures query
  shape from a text-channel observer; it does not bound intermediate-result
  size leakage from an oblivious execution engine. For that, use
  `dp_resize()` (which emits a DP LIMIT) or the plan-layer simulator.
- **`privq_join` provides DP over the loaded catalog**, not per-query. Noise
  is sampled once at `load()` time and reused across `join_order` calls. For
  a fresh ε-DP release per query, build a new `estimator()` each time.
- **The plan-layer simulator never runs MPC** — it threads cardinalities
  through the operator chain and reports a simulated I/O cost using the
  Bater Table 2 cost model. It's an aid for reasoning about strategies, not
  a substitute for running them.

---

## Project structure

```
PrivQ/
├── src/PrivQ/
│   ├── __init__.py         # Public Python API
│   ├── ORQ/                # C++ source for _orq
│   ├── ShrinkWrap/         # C++ source for _shrinkwrap (pads + dp_resize)
│   ├── PrivQJoin/          # C++ source for _privq_join (Laplace + estimator)
│   └── plan/               # Pure-Python plan-layer simulator
├── examples/PrivQ_demo.ipynb
├── pyproject.toml
├── setup.py
├── README.md
└── LICENSE                 # MIT
```

---

## References

- Baum, E. et al. (2025). *ORQ: Complex Analytics on Private Data with Strong
  Security Guarantees.* SOSP 2025.
  [arXiv:2509.10793](https://arxiv.org/abs/2509.10793)
- Bater, J. et al. (2018). *Shrinkwrap: Efficient SQL Query Processing in
  Differentially Private Data Federations.* VLDB 2018.
  [arXiv:1810.01816](https://arxiv.org/abs/1810.01816)

---

## Project author and committee

- **Author:** Alex Garza, M.S. student, Department of Computer Science,
  Tufts University
- **Supervisor:** Dr. Johes Bater

- **Tufts Privacy and Security Lab:** Dr. Daniel Votipka, Dr. Johes bater

## License

MIT — see [LICENSE](LICENSE).
