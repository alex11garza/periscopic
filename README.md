# Periscopic

Periscopic is a privacy-preserving SQL transformation library with C++ extensions.

## What It Includes

- ORQ: normalizes SELECT column order
- Periscopic: differentially private table-size estimation utilities
- ShrinkWrap: structural SQL padding transforms

## Install

```bash
pip install periscopic
```

## Quick Start

```python
import periscopic as p

sql = "SELECT salary, name, age FROM employees"

orq_sql = p.orq(sql)
padded_sql = p.shrinkwrap(orq_sql, padding=True, pad_level=2)
```
