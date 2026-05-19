"""
PrivQ.plan — operator/QueryPlan layer for simulating MPC query strategies.

Build a chain of relational operators and run it under different padding
policies to compare fully-oblivious execution, Shrinkwrap DP resize, and
ORQ-style join-aggregation planning. No real MPC is performed; the
simulator reports per-operator cardinalities and a Bater-Table-2 I/O cost.

Example:
    from PrivQ.plan import (
        Table, QueryPlan, Filter, Join, Aggregate,
        FullObliviousPolicy, DPResizePolicy, OrqPolicy,
    )

    plan = QueryPlan([
        Filter("diagnosis",  predicate="diag == 'hd'",      selectivity=0.01),
        Join("",             "medication",  on="code",      multiplicity=3),
        Join("",             "demographic", on="pid",       multiplicity=1),
        Aggregate(group_by="pid", op="distinct"),
    ])

    tables = [
        Table("diagnosis",   rows=10_000),
        Table("medication",  rows=20_000),
        Table("demographic", rows= 5_000),
    ]

    for policy in [FullObliviousPolicy(),
                   DPResizePolicy(epsilon=1.0, delta=1e-6),
                   OrqPolicy()]:
        print(plan.simulate(tables=tables, policy=policy))
        print()
"""

from .operators import Aggregate, Filter, Join
from .plan import QueryPlan, SimulationReport, StepResult
from .policies import DPResizePolicy, FullObliviousPolicy, OrqPolicy, Policy
from .table import Table

__all__ = [
    "Table",
    "Filter",
    "Join",
    "Aggregate",
    "QueryPlan",
    "SimulationReport",
    "StepResult",
    "Policy",
    "FullObliviousPolicy",
    "DPResizePolicy",
    "OrqPolicy",
]
