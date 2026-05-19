"""
PrivQ — Privacy-preserving SQL query transformation library.

All three pipeline stages are callable directly from this namespace:

    import PrivQ as p

    # ORQ: sort SELECT columns alphabetically
    sql = p.orq("SELECT salary, name, age FROM employees")

    # ShrinkWrap: apply structural padding
    padded = p.shrinkwrap(sql, padding=True, pad_level=2)

    # PrivQ join reorder: DP-estimated join reordering (returns reordered table list)
    ordered = p.privq_join(
        ["orders", "users", "products"],
        catalog=[("users", 100), ("orders", 200), ("products", 50)],
        epsilon=0.5,
    )

    # Full pipeline in one call
    result = p.transform(sql, catalog=[...], epsilon=0.5, padding=True, pad_level=2)

pad_level reference
-------------------
    1  — comment wrapper only (pad_query)
    2  — level 1 + structural pads: column, aggregate, CTE, ORDER BY, subquery  (default)
    3  — level 2 + dummy LEFT JOIN
"""

__version__ = "1.1.2"

from . import _orq        as _orq_mod
from . import _shrinkwrap as _sw_mod
from . import _privq_join as _dp_mod

#----------------------------------------------------------------------------
# Query
#----------------------------------------------------------------------------
class Query:
    """
    A simple wrapper for a SQL query string, allowing for future extensions
    (e.g. storing parsed AST, metadata, etc.) without changing the public API.
    """
    def __init__(self, sql: str):
        self.sql = sql

    def __str__(self):
        return self.sql
    
    def query(self, **kwargs):
        return transform(self.sql, **kwargs)
# ---------------------------------------------------------------------------
# ORQ
# ---------------------------------------------------------------------------

def orq(sql: str) -> str:
    """
    Sort the SELECT column list of a SQL query alphabetically (case-insensitive).

    Normalizes column order to improve AST parse-cache locality and reduce
    side-channel leakage from column position.

    Args:
        sql (str): Input SQL string.

    Returns:
        str: SQL with SELECT columns sorted.  Unchanged if no reorderable
             SELECT list is found (e.g. SELECT * or single column).

    Example:
        >>> import PrivQ as p
        >>> p.orq("SELECT salary, name, age FROM employees")
        'SELECT age, name, salary FROM employees'
    """
    return _orq_mod.sort_query(sql)


# ---------------------------------------------------------------------------
# ShrinkWrap
# ---------------------------------------------------------------------------

def shrinkwrap(sql: str, *, padding: bool = True, pad_level: int = 2) -> str:
    """
    Apply structural padding to a SQL query to obscure its shape.

    An observer watching query traffic cannot infer the original query
    structure (presence of JOINs, aggregates, subqueries, etc.) after padding.

    Args:
        sql       (str):  Input SQL string.
        padding   (bool): If False, returns the query unchanged. Default True.
        pad_level (int):  Controls how many padding layers are applied.
                          1 — comment wrapper only
                          2 — level 1 + column, aggregate, CTE, ORDER BY, subquery pads  (default)
                          3 — level 2 + dummy LEFT JOIN

    Returns:
        str: Padded SQL string.

    Example:
        >>> import PrivQ as p
        >>> p.shrinkwrap("SELECT * FROM users", padding=True, pad_level=2)
    """
    if not padding:
        return sql

    result = sql

    # Level 1 — comment wrapper (always applied when padding=True)
    result = _sw_mod.pad_query(result)

    if pad_level >= 2:
        result = _sw_mod.pad_column(result)
        result = _sw_mod.pad_aggregate(result)
        result = _sw_mod.pad_cte(result)
        result = _sw_mod.pad_orderby(result)
        result = _sw_mod.pad_subquery(result)

    if pad_level >= 3:
        result = _sw_mod.pad_join(result)

    return result


def truncated_laplace(
    epsilon: float,
    delta: float,
    sensitivity: float = 1.0,
) -> int:
    """
    Sample integer noise from the truncated Laplace mechanism of Bater et al.
    (Shrinkwrap, VLDB 2018, Def. 4).

    Returns a non-negative integer eta such that Pr[eta < sensitivity] <= delta,
    drawn from a Laplace(scale=sensitivity/epsilon) centered at the paper's
    shift eta_0 and clamped to max(eta, 0).

    Args:
        epsilon     (float): Privacy budget for this release. Must be > 0.
        delta       (float): Failure probability. Must be in (0, 1).
        sensitivity (float): Query sensitivity Delta_c (default 1.0, counting query).

    Returns:
        int: Non-negative integer noise sample.

    Example:
        >>> import PrivQ as p
        >>> p.truncated_laplace(1.0, 1e-5, 1.0)  # doctest: +SKIP
        12
    """
    return _sw_mod.truncated_laplace(epsilon, delta, sensitivity)


def dp_resize(
    sql: str,
    true_count: int,
    *,
    epsilon: float,
    delta: float,
    sensitivity: float = 1.0,
) -> str:
    """
    Append (or replace) a SQL LIMIT clause with a differentially-private
    upper bound on the result cardinality, implementing the Resize step
    from Bater et al. Shrinkwrap Algorithm 1 at the SQL-text layer.

    Computes c_tilde = true_count + truncated_laplace(epsilon, delta, sensitivity)
    and rewrites the SQL so its result is bounded by LIMIT c_tilde. The DP
    guarantee applies to the released LIMIT value: any two neighboring
    databases differing by `sensitivity` rows produce LIMIT distributions
    within e^epsilon (with failure probability delta).

    If the input SQL already ends with `LIMIT n`, that LIMIT is replaced;
    a trailing semicolon is preserved. LIMITs inside subqueries are not
    touched — they belong to a different operator with its own sensitivity.

    Args:
        sql         (str):   Input SQL string.
        true_count  (int):   True (non-private) result cardinality. Must be >= 0.
        epsilon     (float): Privacy budget. Must be > 0.
        delta       (float): Failure probability. Must be in (0, 1).
        sensitivity (float): Sensitivity Delta_c of the cardinality query.
                             Default 1.0 (counting query: adding/removing
                             one row changes the count by at most one).

    Returns:
        str: SQL string with a DP-noised LIMIT clause.

    Example:
        >>> import PrivQ as p
        >>> p.dp_resize("SELECT name FROM users", 100, epsilon=1.0, delta=1e-5)
        # 'SELECT name FROM users LIMIT 112'  (exact value is random)
    """
    return _sw_mod.dp_resize(sql, true_count, epsilon, delta, sensitivity)


def shrinkwrap_pad(sql: str, pad: str) -> str:
    """
    Apply a single named ShrinkWrap pad to a SQL query.

    Useful when you want to apply pads individually rather than by level.

    Args:
        sql (str): Input SQL string.
        pad (str): One of: 'query', 'column', 'aggregate', 'cte',
                   'join', 'orderby', 'subquery', 'insert', 'update', 'delete'

    Returns:
        str: SQL with the specified pad applied.

    Raises:
        ValueError: If pad name is not recognised.

    Example:
        >>> import PrivQ as p
        >>> p.shrinkwrap_pad("SELECT * FROM users", "column")
    """
    _pads = {
        "query":     _sw_mod.pad_query,
        "column":    _sw_mod.pad_column,
        "aggregate": _sw_mod.pad_aggregate,
        "cte":       _sw_mod.pad_cte,
        "join":      _sw_mod.pad_join,
        "orderby":   _sw_mod.pad_orderby,
        "subquery":  _sw_mod.pad_subquery,
        "insert":    _sw_mod.pad_insert,
        "update":    _sw_mod.pad_update,
        "delete":    _sw_mod.pad_delete,
    }
    if pad not in _pads:
        raise ValueError(
            f"Unknown pad '{pad}'. Choose from: {', '.join(sorted(_pads))}"
        )
    return _pads[pad](sql)


# ---------------------------------------------------------------------------
# PrivQ join reorder (DP table size estimator)
# ---------------------------------------------------------------------------

def privq_join(
    tables: list,
    catalog: list,
    *,
    epsilon: float = 0.5,
) -> list:
    """
    Reorder a list of table names smallest → largest using differentially
    private size estimates from the given catalog.

    True row counts from the catalog are never stored — Laplace(1/epsilon)
    noise is added before insertion into the internal hash map + min-heap,
    satisfying epsilon-differential privacy.

    Args:
        tables  (list[str]):             Table names from a FROM/JOIN clause.
        catalog (list[tuple[str, int]]): List of (table_name, true_row_count)
                                         pairs, e.g. from pg_class.reltuples.
        epsilon (float):                 Privacy budget (default 0.5).
                                         Smaller => more noise => more privacy.

    Returns:
        list[str]: Input table names reordered smallest → largest.
                   Tables not in the catalog are sorted last.

    Example:
        >>> import PrivQ as p
        >>> p.privq_join(
        ...     ["orders", "users"],
        ...     catalog=[("users", 100), ("orders", 200)],
        ...     epsilon=0.5,
        ... )
        ['users', 'orders']
    """
    est = _dp_mod.TableSizeEstimator(epsilon)
    est.load(catalog)
    return est.join_order(tables)


def estimator(catalog: list, *, epsilon: float = 0.5) -> _dp_mod.TableSizeEstimator:
    """
    Build and return a loaded TableSizeEstimator for repeated use.

    Prefer this over calling privq_join() in a loop — create one estimator
    and reuse it across queries so the heap is only built once.

    Args:
        catalog (list[tuple[str, int]]): List of (table_name, true_row_count) pairs.
        epsilon (float):                 Privacy budget (default 0.5).

    Returns:
        TableSizeEstimator: Loaded estimator ready for join_order() calls.

    Example:
        >>> import PrivQ as p
        >>> est = p.estimator([("users", 100), ("orders", 200)], epsilon=0.5)
        >>> est.join_order(["orders", "users"])
        ['users', 'orders']
    """
    est = _dp_mod.TableSizeEstimator(epsilon)
    est.load(catalog)
    return est


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def transform(
    sql: str,
    *,
    catalog: list | None = None,
    epsilon: float = 0.5,
    padding: bool = True,
    pad_level: int = 2,
) -> dict:
    """
    Run the full PrivQ pipeline on a SQL query and return each stage's output.

    Stages (in order):
        1. ORQ        — sort SELECT columns alphabetically
        2. PrivQ join — compute DP join order from catalog (if catalog given)
        3. ShrinkWrap — apply structural padding to the ORQ output

    The library does not rewrite the FROM/JOIN clause itself — the caller
    (typically a server layer with a real SQL parser) is expected to apply
    the returned 'join_order' to the SQL.

    Args:
        sql       (str):                    Input SQL string.
        catalog   (list[tuple[str, int]] | None): Table size catalog for join
                                            reordering. If None, step 2 is skipped.
        epsilon   (float):                  DP privacy budget (default 0.5).
        padding   (bool):                   Whether to apply ShrinkWrap (default True).
        pad_level (int):                    ShrinkWrap padding level 1–3 (default 2).

    Returns:
        dict with keys:
            'original'    — input SQL
            'orq'         — after ORQ column sort
            'join_order'  — DP-noisy table ordering (list[str]), or None if no catalog
            'shrinkwrap'  — final padded SQL (built from the ORQ output)

    Example:
        >>> import PrivQ as p
        >>> result = p.transform(
        ...     "SELECT salary, name FROM orders JOIN users ON orders.user_id = users.id",
        ...     catalog=[("users", 100), ("orders", 200)],
        ...     epsilon=0.5,
        ...     padding=True,
        ...     pad_level=2,
        ... )
        >>> print(result['shrinkwrap'])
    """
    orq_sql = orq(sql)

    join_order = None
    if catalog:
        est = _dp_mod.TableSizeEstimator(epsilon)
        est.load(catalog)
        join_order = est.join_order([name for name, _ in catalog])

    padded_sql = shrinkwrap(orq_sql, padding=padding, pad_level=pad_level)

    return {
        "original":   sql,
        "orq":        orq_sql,
        "join_order": join_order,
        "shrinkwrap": padded_sql,
    }


# ---------------------------------------------------------------------------
# Re-export low-level modules for advanced use
# ---------------------------------------------------------------------------
TableSizeEstimator = _dp_mod.TableSizeEstimator
laplace_sample     = _dp_mod.laplace_sample
noisy_count        = _dp_mod.noisy_count

# ---------------------------------------------------------------------------
# Plan-layer simulator (PrivQ.plan) — convenience top-level re-exports
# ---------------------------------------------------------------------------
from .plan import (
    Aggregate,
    DPResizePolicy,
    Filter,
    FullObliviousPolicy,
    Join,
    OrqPolicy,
    QueryPlan,
    SimulationReport,
    StepResult,
    Table,
)

__all__ = [
    "orq",
    "shrinkwrap",
    "shrinkwrap_pad",
    "truncated_laplace",
    "dp_resize",
    "privq_join",
    "estimator",
    "transform",
    "TableSizeEstimator",
    "laplace_sample",
    "noisy_count",
    # plan layer
    "Table",
    "QueryPlan",
    "Filter",
    "Join",
    "Aggregate",
    "SimulationReport",
    "StepResult",
    "FullObliviousPolicy",
    "DPResizePolicy",
    "OrqPolicy",
]
