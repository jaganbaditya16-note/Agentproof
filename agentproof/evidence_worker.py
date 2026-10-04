from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any


def run_worker(payload: dict[str, Any]) -> dict[str, Any]:
    repo = Path(payload["repo"])
    module_name = payload["module"]
    function_name = payload["function"]
    cases = payload["cases"]

    try:
        if str(repo) not in sys.path:
            sys.path.insert(0, str(repo))

        module_path = repo / (module_name.replace(".", "/") + ".py")

        if not module_path.is_file():
            raise FileNotFoundError(
                f"Evidence module file was not found: {module_path}"
            )

        import types

        module = types.ModuleType(
            f"_agentproof_worker_{module_name.replace('.', '_')}"
        )
        module.__file__ = str(module_path)

        source = module_path.read_text(encoding="utf-8-sig")
        code = compile(source, str(module_path), "exec")
        exec(code, module.__dict__)
        function = getattr(module, function_name, None)

        if not callable(function):
            return {
                "status": "FAIL",
                "module": module_name,
                "function": function_name,
                "cases": [],
                "passed": 0,
                "failed": 0,
                "error": f"Function '{function_name}' was not found.",
            }

        results = []
        passed = 0
        failed = 0

        for index, case in enumerate(cases, start=1):
            expected = case["expected"]

            try:
                actual = function(case["input"])
                case_passed = actual == expected
                error = None
            except Exception as exc:
                actual = None
                case_passed = False
                error = str(exc)

            results.append(
                {
                    "case": index,
                    "input": case["input"],
                    "expected": expected,
                    "actual": actual,
                    "status": "PASS" if case_passed else "FAIL",
                    "error": error,
                }
            )

            if case_passed:
                passed += 1
            else:
                failed += 1

        return {
            "status": "PASS" if failed == 0 else "FAIL",
            "module": module_name,
            "function": function_name,
            "cases": results,
            "passed": passed,
            "failed": failed,
            "error": None,
        }

    except Exception as exc:
        return {
            "status": "UNKNOWN",
            "module": module_name,
            "function": function_name,
            "cases": [],
            "passed": 0,
            "failed": 0,
            "error": str(exc),
        }


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        result = run_worker(payload)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "UNKNOWN",
                    "cases": [],
                    "passed": 0,
                    "failed": 0,
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()

