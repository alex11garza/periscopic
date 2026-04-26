"""
setup.py — Build the periscopic Python extension package.

Compiles three pybind11 C++ extension modules from src/periscopic:
    _orq          <- src/periscopic/ORQ/orq_sort_query.cpp  + bindings.cpp
    _shrinkwrap   <- src/periscopic/ShrinkWrap/pad_*.cpp    + bindings.cpp
    _periscopic   <- src/periscopic/Periscopic/*.cpp        + bindings.cpp

Build in-place for development:
    python setup.py build_ext --inplace
"""

from setuptools import setup, Extension
import pybind11

INC = pybind11.get_include()
COMPILE_ARGS = ["-std=c++17", "-O2", "-Wall"]

# _orq
ext_orq = Extension(
    name="periscopic._orq",
    sources=[
        "src/periscopic/ORQ/orq_sort_query.cpp",
        "src/periscopic/ORQ/bindings.cpp",
    ],
    include_dirs=[INC, "src/periscopic/ORQ"],
    extra_compile_args=COMPILE_ARGS,
    language="c++",
)

# _shrinkwrap
ext_shrinkwrap = Extension(
    name="periscopic._shrinkwrap",
    sources=[
        "src/periscopic/ShrinkWrap/pad_aggregate.cpp",
        "src/periscopic/ShrinkWrap/pad_column.cpp",
        "src/periscopic/ShrinkWrap/pad_cte.cpp",
        "src/periscopic/ShrinkWrap/pad_delete.cpp",
        "src/periscopic/ShrinkWrap/pad_insert.cpp",
        "src/periscopic/ShrinkWrap/pad_join.cpp",
        "src/periscopic/ShrinkWrap/pad_orderby.cpp",
        "src/periscopic/ShrinkWrap/pad_query.cpp",
        "src/periscopic/ShrinkWrap/pad_subquery.cpp",
        "src/periscopic/ShrinkWrap/pad_update.cpp",
        "src/periscopic/ShrinkWrap/bindings.cpp",
    ],
    include_dirs=[INC, "src/periscopic/ShrinkWrap"],
    extra_compile_args=COMPILE_ARGS,
    language="c++",
)

# _periscopic
ext_periscopic = Extension(
    name="periscopic._periscopic",
    sources=[
        "src/periscopic/Periscopic/laplace.cpp",
        "src/periscopic/Periscopic/min_heap.cpp",
        "src/periscopic/Periscopic/table_size_estimator.cpp",
        "src/periscopic/Periscopic/bindings.cpp",
    ],
    include_dirs=[INC, "src/periscopic/Periscopic"],
    extra_compile_args=COMPILE_ARGS,
    language="c++",
)

setup(
    name="periscopic",
    version="0.1.1",
    description="Privacy-preserving SQL transformations with ORQ, ShrinkWrap, and differential privacy utilities",
    packages=["periscopic"],
    package_dir={"": "src"},
    ext_modules=[ext_orq, ext_shrinkwrap, ext_periscopic],
    python_requires=">=3.9",
)
