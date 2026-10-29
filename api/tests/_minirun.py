"""Fallback test runner for environments without pytest (CI uses pytest).

Runs every test_* function in tests/test_*.py, providing the `kb` fixture from conftest.
"""

from __future__ import annotations

import importlib
import inspect
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class _Skip(Exception):
    pass


class _PytestShim:
    @staticmethod
    def importorskip(name):
        try:
            return importlib.import_module(name)
        except ImportError as e:
            raise _Skip(name) from e

    @staticmethod
    def fixture(fn=None, **_):
        return fn if fn else (lambda f: f)


def main() -> int:
    sys.modules.setdefault("pytest", _PytestShim())  # type: ignore[arg-type]
    conftest = importlib.import_module("tests.conftest")
    passed = failed = skipped = 0
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        mod = importlib.import_module(f"tests.{path.stem}")
        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            kwargs = {}
            if "kb" in inspect.signature(fn).parameters:
                kwargs["kb"] = (
                    conftest.kb.__wrapped__(Path(tempfile.mkdtemp()))
                    if hasattr(conftest.kb, "__wrapped__")
                    else conftest.kb(Path(tempfile.mkdtemp()))
                )
            try:
                fn(**kwargs)
                passed += 1
                print(f"PASS {path.stem}::{name}")
            except _Skip as s:
                skipped += 1
                print(f"SKIP {path.stem}::{name} (needs {s})")
            except Exception:
                failed += 1
                print(f"FAIL {path.stem}::{name}\n{traceback.format_exc()}")
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
