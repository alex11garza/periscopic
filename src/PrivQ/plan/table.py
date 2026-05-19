"""
Table — schema descriptor for the plan-layer simulator.

A Table carries only a name and a true row count. The simulator never
materializes tuples; it reasons about cardinalities flowing through
operators under different padding policies.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Table:
    """A named relation with a known row count.

    Args:
        name (str): Identifier used by operators to reference this table.
        rows (int): True cardinality. Must be >= 0.

    Example:
        >>> from PrivQ.plan import Table
        >>> Table("diagnosis", rows=10_000)
        Table(name='diagnosis', rows=10000)
    """
    name: str
    rows: int

    def __post_init__(self) -> None:
        if self.rows < 0:
            raise ValueError(f"Table.rows must be >= 0, got {self.rows}")
