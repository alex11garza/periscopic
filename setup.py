"""
setup.py — Build the PrivQ Python extension package.

Compiles three pybind11 C++ extension modules from src/PrivQ:
    _orq          <- src/PrivQ/ORQ/orq_sort_query.cpp    + bindings.cpp
    _shrinkwrap   <- src/PrivQ/ShrinkWrap/pad_*.cpp      + bindings.cpp
    _privq_join   <- src/PrivQ/PrivQJoin/*.cpp           + bindings.cpp

Build in-place for development:
    python setup.py build_ext --inplace
"""

from setuptools import setup, Extension
import pybind11

INC = pybind11.get_include()
COMPILE_ARGS = ["-std=c++17", "-O2", "-Wall"]

# _orq
ext_orq = Extension(
    name="PrivQ._orq",
    sources=[
        "src/PrivQ/ORQ/orq_sort_query.cpp",
        "src/PrivQ/ORQ/bindings.cpp",
    ],
    include_dirs=[INC, "src/PrivQ/ORQ"],
    extra_compile_args=COMPILE_ARGS,
    language="c++",
)

# _shrinkwrap
ext_shrinkwrap = Extension(
    name="PrivQ._shrinkwrap",
    sources=[
        "src/PrivQ/ShrinkWrap/pad_aggregate.cpp",
        "src/PrivQ/ShrinkWrap/pad_column.cpp",
        "src/PrivQ/ShrinkWrap/pad_cte.cpp",
        "src/PrivQ/ShrinkWrap/pad_delete.cpp",
        "src/PrivQ/ShrinkWrap/pad_insert.cpp",
        "src/PrivQ/ShrinkWrap/pad_join.cpp",
        "src/PrivQ/ShrinkWrap/pad_orderby.cpp",
        "src/PrivQ/ShrinkWrap/pad_query.cpp",
        "src/PrivQ/ShrinkWrap/pad_subquery.cpp",
        "src/PrivQ/ShrinkWrap/pad_update.cpp",
        "src/PrivQ/ShrinkWrap/dp_resize.cpp",
        "src/PrivQ/ShrinkWrap/bindings.cpp",
    ],
    include_dirs=[INC, "src/PrivQ/ShrinkWrap"],
    extra_compile_args=COMPILE_ARGS,
    language="c++",
)

# _privq_join
ext_privq_join = Extension(
    name="PrivQ._privq_join",
    sources=[
        "src/PrivQ/PrivQJoin/laplace.cpp",
        "src/PrivQ/PrivQJoin/min_heap.cpp",
        "src/PrivQ/PrivQJoin/table_size_estimator.cpp",
        "src/PrivQ/PrivQJoin/bindings.cpp",
    ],
    include_dirs=[INC, "src/PrivQ/PrivQJoin"],
    extra_compile_args=COMPILE_ARGS,
    language="c++",
)

setup(
    name="PrivQ",
    version="1.1.2",
    description="Privacy-preserving SQL transformations with ORQ, ShrinkWrap, and differential privacy utilities",
    packages=["PrivQ", "PrivQ.plan"],
    package_dir={"": "src"},
    ext_modules=[ext_orq, ext_shrinkwrap, ext_privq_join],
    python_requires=">=3.9",
)
