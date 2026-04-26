"""
periscopic — Privacy-preserving SQL query transformation library.

All three pipeline stages are callable directly from this namespace:

    import periscopic as p

    # ORQ: sort SELECT columns alphabetically
    sql = p.orq("SELECT salary, name, age FROM employees")

    # ShrinkWrap: apply structural padding
    padded = p.shrinkwrap(sql, padding=True, pad_level=2)

    # Periscopic: DP-estimated join reordering (returns reordered table list)
    ordered = p.periscopic(
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

__version__ = "1.0.0"

from . import _orq        as _orq_mod
from . import _shrinkwrap as _sw_mod
from . import _periscopic as _dp_mod


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
        >>> import periscopic as p
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
        >>> import periscopic as p
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
        >>> import periscopic as p
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
# Periscopic (DP table size estimator)
# ---------------------------------------------------------------------------

def periscopic(
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
        >>> import periscopic as p
        >>> p.periscopic(
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

    Prefer this over calling periscopic() in a loop — create one estimator
    and reuse it across queries so the heap is only built once.

    Args:
        catalog (list[tuple[str, int]]): List of (table_name, true_row_count) pairs.
        epsilon (float):                 Privacy budget (default 0.5).

    Returns:
        TableSizeEstimator: Loaded estimator ready for join_order() calls.

    Example:
        >>> import periscopic as p
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
    Run the full Periscopic pipeline on a SQL query and return each stage's output.

    Stages (in order):
        1. ORQ        — sort SELECT columns alphabetically
        2. Periscopic — compute DP join order from catalog (if catalog given)
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
        >>> import periscopic as p
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

__all__ = [
    "orq",
    "shrinkwrap",
    "shrinkwrap_pad",
    "periscopic",
    "estimator",
    "transform",
    "TableSizeEstimator",
    "laplace_sample",
    "noisy_count",
]
