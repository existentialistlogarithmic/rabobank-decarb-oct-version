"""The layering IS the deliverable, not just an aesthetic.

Group order in the package mirrors Part 1 of Appendix A: money first, decision
second, uncertainty third, constraints last.  A newcomer must be able to stop
reading at any group boundary and still have a working, if incomplete, model -
which only holds if the imports never point backwards.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

PKG = pathlib.Path(__file__).resolve().parents[1] / "timing_model"

#: Strict order.  A module may import only from STRICTLY lower levels.
#: ``params`` is level 0: it is the parameter container, not a group.
LEVELS: dict[str, int] = {
    "params": 0,
    "primitives": 1,   # Group I
    "benefit": 2,      # Group II
    "cost": 3,         # Group III
    "objective": 4,    # Group IV
    "option": 5,       # Group V
    "validate": 6,
    "results": 7,
    "scenarios": 8,
    "report": 9,
    "diff_harness": 10,   # imports report for the Table alias
}


def _imports(module: str) -> set[str]:
    """Package-internal modules imported by ``module``, by AST walk."""
    tree = ast.parse((PKG / f"{module}.py").read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "timing_model"
        ):
            parts = (node.module or "").split(".")
            if len(parts) > 1:
                found.add(parts[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("timing_model."):
                    found.add(alias.name.split(".")[1])
    return found


@pytest.mark.parametrize("module", sorted(LEVELS))
def test_imports_point_only_downwards(module: str) -> None:
    for dep in _imports(module):
        assert dep in LEVELS, f"{module} imports unknown package module {dep}"
        assert LEVELS[dep] < LEVELS[module], (
            f"{module} (level {LEVELS[module]}) imports {dep} "
            f"(level {LEVELS[dep]}): the group order runs forward only"
        )


def test_cost_does_not_import_objective() -> None:
    """Stated explicitly in Appendix A §4.1."""
    assert "objective" not in _imports("cost")


def test_primitives_imports_only_the_parameter_container() -> None:
    """Group I is the bottom of the dependency order.

    ``primitives`` may reference ``params`` (it needs the dataclasses for its
    type hints) but nothing else in the package.
    """
    assert _imports("primitives") <= {"params"}


def test_load_factor_never_touches_the_cost_side() -> None:
    """Appendix A F2: u multiplies B(t) only, never I'(T).

    Checked at the source level because this is a unit error, and a unit error
    that is merely absent from today's numbers can reappear in tomorrow's.
    """
    src = (PKG / "cost.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "u":
            pytest.fail("cost.py reads the load factor u; it must not (F2)")


def test_every_public_function_has_a_docstring() -> None:
    """Docstrings cite the spec; a missing one is a missing citation."""
    missing: list[str] = []
    for module in sorted(LEVELS):
        tree = ast.parse((PKG / f"{module}.py").read_text())
        for node in tree.body:
            if (isinstance(node, (ast.FunctionDef, ast.ClassDef))
                    and not node.name.startswith("_")
                    and not ast.get_docstring(node)):
                missing.append(f"{module}.{node.name}")
    assert not missing, f"missing docstrings: {missing}"


# --------------------------------------------------------------------------
# Top-level packages. Same rule as the model's group order, one level up: a
# layer may import from lower layers only, so a reader can stop at any package
# boundary and still have something that runs.
# --------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Strict order. `data` deliberately sits BELOW the model and must not import
#: it: an observation is not allowed to depend on what the model does with it.
PACKAGE_LEVELS: dict[str, int] = {
    "timing_model": 0,
    "data": 1,
    "analysis": 2,
    "reporting": 3,
}

LOCAL_PACKAGES = set(PACKAGE_LEVELS)


def _package_imports(path: pathlib.Path) -> set[str]:
    """Top-level local packages imported by one file, by AST walk."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            head = (node.module or "").split(".")[0]
            if head in LOCAL_PACKAGES:
                found.add(head)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                head = alias.name.split(".")[0]
                if head in LOCAL_PACKAGES:
                    found.add(head)
    return found


@pytest.mark.parametrize("package", sorted(PACKAGE_LEVELS))
def test_packages_import_only_downwards(package: str) -> None:
    level = PACKAGE_LEVELS[package]
    for path in sorted((ROOT / package).glob("*.py")):
        for dep in _package_imports(path) - {package}:
            assert PACKAGE_LEVELS[dep] < level, (
                f"{package}/{path.name} imports {dep} "
                f"(level {PACKAGE_LEVELS[dep]} >= {level}): layers run one way"
            )


def test_observed_data_does_not_depend_on_the_model() -> None:
    """`data` answers "what is true", not "what does the model need".

    If a provider imported `timing_model` it would be a short step to shaping a
    series to suit an assumption, which is the failure this whole layer exists
    to prevent.
    """
    for path in sorted((ROOT / "data").glob("*.py")):
        assert "timing_model" not in _package_imports(path), path.name


def test_nothing_below_reporting_imports_reporting() -> None:
    """Generated pages are leaves. The model must never read its own report."""
    for package in ("timing_model", "data", "analysis"):
        for path in sorted((ROOT / package).glob("*.py")):
            assert "reporting" not in _package_imports(path), f"{package}/{path.name}"
