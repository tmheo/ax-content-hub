---
description: Run all code quality checks (pytest, ruff check, ruff format, mypy) in sequence with consolidated results.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

This command automates the complete code quality verification workflow by running all quality checks in sequence.

### Checks Performed

1. **pytest** - Run all tests with verbose output
2. **ruff check** - Lint code and auto-fix issues
3. **ruff format** - Format code to consistent style
4. **mypy** - Static type checking

### Execution

1. **Parse arguments** (optional):
   - `--fix` (default): Auto-fix linting issues with ruff
   - `--no-fix`: Only report issues without fixing
   - `--fast`: Skip pytest, only run linting/formatting
   - `--paths [paths]`: Specify custom paths (default: `src/ tests/`)

2. **Run checks sequentially**:

   ```bash
   # Step 1: Run tests (unless --fast)
   uv run pytest tests/ -v

   # Step 2: Lint and fix
   uv run ruff check --fix src/ tests/

   # Step 3: Format code
   uv run ruff format src/ tests/

   # Step 4: Type check
   uv run mypy src/
   ```

3. **Collect results** from each command:
   - Exit code (0 = success, non-zero = failure)
   - Summary of issues found/fixed
   - Timing for each step

4. **Generate consolidated report**:

   ```
   Quality Checks Summary

   | Check       | Status | Details                    | Time    |
   |-------------|--------|----------------------------|---------|
   | pytest      | PASS   | 142 tests passed           | 12.3s   |
   | ruff check  | PASS   | 3 issues fixed             | 0.8s    |
   | ruff format | PASS   | 2 files reformatted        | 0.4s    |
   | mypy        | PASS   | No type errors             | 5.2s    |

   Overall: PASS (all checks passed)
   Total time: 18.7s
   ```

### Error Handling

- **Continue on failure**: All checks run even if earlier ones fail
- **Detailed error output**: Show specific errors for failed checks
- **Fix suggestions**: Provide actionable next steps for failures

Example failure report:
```
Quality Checks Summary

| Check       | Status | Details                    | Time    |
|-------------|--------|----------------------------|---------|
| pytest      | FAIL   | 3 tests failed, 139 passed | 11.8s   |
| ruff check  | PASS   | 0 issues                   | 0.7s    |
| ruff format | PASS   | 0 files changed            | 0.3s    |
| mypy        | FAIL   | 2 type errors              | 4.9s    |

Overall: FAIL (2 checks failed)

Failed Tests:
  - tests/unit/test_auth.py::test_login_invalid - AssertionError
  - tests/unit/test_auth.py::test_logout - AttributeError
  - tests/integration/test_api.py::test_rate_limit - TimeoutError

Type Errors:
  - src/services/auth.py:45: error: Argument 1 has incompatible type "str"; expected "int"
  - src/models/user.py:23: error: Missing return statement

Next Steps:
  1. Fix failing tests in tests/unit/test_auth.py
  2. Resolve type errors in src/services/auth.py and src/models/user.py
  3. Re-run: /run-quality-checks
```

## Options

| Option | Description |
|--------|-------------|
| `--fix` | Auto-fix linting issues (default) |
| `--no-fix` | Only report issues, don't auto-fix |
| `--fast` | Skip pytest, only run linting/formatting/typing |
| `--paths [paths]` | Custom paths to check (default: `src/ tests/`) |

## Examples

```bash
# Run all checks with auto-fix (default)
/run-quality-checks

# Only run linting and formatting (skip tests)
/run-quality-checks --fast

# Check without auto-fixing
/run-quality-checks --no-fix

# Check specific paths
/run-quality-checks --paths src/agent/ tests/unit/
```

## Notes

- Requires `uv` package manager to be installed
- All checks use project's `pyproject.toml` configuration
- Ruff check runs with `--fix` by default for developer convenience
- MyPy only checks `src/` to avoid test file type issues
- For CI environments, consider using `--no-fix` to ensure reproducibility
