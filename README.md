# AI CI Doctor

A small Python release gate and GitHub Actions pipeline for practicing evidence-driven, AI-assisted CI failure investigation.

This project follows a reproducible debugging story: a percentage-versus-fraction defect produces failing boundary tests and red CI; a focused, Copilot-assisted correction restores the intended decisions; an incident report records the cause; and a separate empty-check guard adds a fourth regression test.

The final gate allows failure rates at or below **5%**, blocks rates above **5%**, and rejects nonpositive totals in `should_deploy`. The supplied Actions screenshots show successful runs for both the unit correction and the later guard.

## Contents

- [Architecture](#architecture)
- [Release-gate logic](#release-gate-logic)
- [The original bug](#the-original-bug)
- [Tests and boundaries](#tests-and-boundaries)
- [GitHub Actions](#github-actions)
- [Copilot-assisted investigation and review](#copilot-assisted-investigation-and-review)
- [Incident report](#incident-report)
- [Empty-check guard](#empty-check-guard)
- [Setup and execution](#setup-and-execution)
- [Project structure](#project-structure)
- [Red-to-green results](#red-to-green-results)
- [Lessons learned](#lessons-learned)

## Architecture

The project has one application module, a standard-library test suite, and a CI workflow.

```text
Demo execution
  main()
    -> describe_decision(failed_checks, total_checks)
         -> should_deploy(failed_checks, total_checks)
         -> formatted DEPLOY or BLOCK message

Verification
  Local command / GitHub Actions
    -> python -m unittest
         -> tests/test_release_gate.py
              -> should_deploy(...)
```

| Component | Responsibility |
| --- | --- |
| `MAX_FAILURE_RATE` | Stores the default fractional budget, `0.05`. |
| `should_deploy` | Validates the total and returns a Boolean decision. Accepts an optional threshold argument. |
| `describe_decision` | Calculates the display rate, calls the gate with its default budget, and returns a readable message. |
| `main` | Prints decisions for the two built-in examples: `(0, 100)` and `(6, 100)`. |
| `ReleaseGateTests` | Verifies the below-budget, at-budget, above-budget, and empty-check behaviors. |
| `.github/workflows/ci.yml` | Runs the unit tests for configured push and pull-request events. |
| `INCIDENT_REPORT.md` | Records the observed failures, root cause, resolution, and prevention guidance. |

`DEPLOY` and `BLOCK` are output labels. The script does not perform a deployment, and the workflow runs tests rather than invoking a deployment stage. Copilot is part of the development workflow; the Python module contains no AI service integration.

## Release-gate logic

The policy uses a decimal fraction:

```text
failure_rate = failed_checks / total_checks
allow when failure_rate <= max_failure_rate
default max_failure_rate = 0.05
```

The implemented core function is:

```python
MAX_FAILURE_RATE = 0.05


def should_deploy(failed_checks, total_checks, max_failure_rate=MAX_FAILURE_RATE):
    if total_checks <= 0:
        raise ValueError("total_checks must be greater than zero")

    failure_rate = failed_checks / total_checks
    return failure_rate <= max_failure_rate
```

The `<=` operator is intentional: exactly 5% is allowed. A custom budget must also be supplied as a fraction, such as `0.02` for 2%.

| Failed checks | Total checks | Fraction | Display rate | Default decision |
| ---: | ---: | ---: | ---: | --- |
| 0 | 100 | 0.00 | 0.0% | `True` / `DEPLOY` |
| 1 | 100 | 0.01 | 1.0% | `True` / `DEPLOY` |
| 5 | 100 | 0.05 | 5.0% | `True` / `DEPLOY` |
| 6 | 100 | 0.06 | 6.0% | `False` / `BLOCK` |
| 0 | 0 | Undefined | Undefined | `should_deploy` raises `ValueError` |

The display helper uses `f"({failure_rate:.1%}): {decision}"`. This formats a fraction as a percentage with one decimal place without changing the numeric value used by the gate.

## The original bug

The initial implementation converted the fraction to percentage points, then compared it with a fractional threshold:

```python
failure_percent = failed_checks / total_checks * 100
return failure_percent <= max_failure_rate
```

With the default threshold:

| Input | Buggy comparison | Original result | Expected result |
| --- | --- | --- | --- |
| `should_deploy(1, 100)` | `1.0 <= 0.05` | `False` | `True` |
| `should_deploy(5, 100)` | `5.0 <= 0.05` | `False` | `True` |
| `should_deploy(6, 100)` | `6.0 <= 0.05` | `False` | `False` |

For positive totals, the original comparison effectively enforced a 0.05% failure budget rather than 5%. The two built-in demo inputs did not reveal the problem: 0% passed and 6% was blocked under both implementations.

The repair removed `* 100` from both calculations, renamed `failure_percent` to `failure_rate`, and changed the display formatting to `.1%`. The configured budget and the inclusive comparison stayed unchanged.

The initial defect is preserved in commit [`a217641`](https://github.com/AyeFuad2/ai-ci-doctor/commit/a217641); the unit correction is in [`cf45ff4`](https://github.com/AyeFuad2/ai-ci-doctor/commit/cf45ff4).

## Tests and boundaries

The project uses Python's built-in `unittest` module. The current suite has four tests:

| Test | Input | Assertion | Purpose |
| --- | --- | --- | --- |
| `test_allows_release_below_budget` | `(1, 100)` | `assertTrue` | A rate inside the budget must pass. |
| `test_allows_release_at_budget` | `(5, 100)` | `assertTrue` | Equality at the threshold must pass. |
| `test_blocks_release_above_budget` | `(6, 100)` | `assertFalse` | A rate above the threshold must be blocked. |
| `test_rejects_empty_check_set` | `(0, 0)` | `assertRaisesRegex` for `ValueError` | An empty set must produce the explicit validation error. |

The original three-test run had two failures: below-budget and at-budget. After the unit correction, those same three tests passed. The empty-check regression later expanded the suite to four tests.

Run from the repository root:

```bash
python -m unittest
```

For named results:

```bash
python -m unittest -v
```

A successful current run reports four tests and `OK`. The checked-in suite exercises `should_deploy`; it does not test the display helper, arbitrary threshold overrides, or every possible invalid input.

## GitHub Actions

The checked-in workflow is named `CI` and lives at [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

It runs on pushes to `main` and pull requests targeting `main`. It grants `contents: read` and has one `test` job on `ubuntu-latest`:

1. Check out the repository with `actions/checkout@v7.0.1`.
2. Set up Python with `actions/setup-python@v7.0.0`, requesting Python `3.14.8`.
3. Run `python -m unittest`.

These versions describe the current checked-in configuration. The screenshots document the captured run outcomes; they do not display the runner's Python version.

The workflow has no dependency-install step because the application and tests use the Python standard library. A failing assertion or unhandled test error makes the test command fail and produces a red CI result; a passing suite produces a green result.

The incident report recommends requiring green CI before accepting future gate changes. The workflow itself does not establish branch protection or required-check rules.

## Copilot-assisted investigation and review

The investigation centered on a concrete discrepancy: `should_deploy(1, 100)` and `should_deploy(5, 100)` returned false despite the configured 5% budget. The arithmetic and test assertions identify the cause without needing to change the policy.

The supplied Copilot session captures a constrained repair request: modify only `release_gate.py`, rename the rate variable in both functions, remove the multiplication by 100, and use `.1%` for display. Copilot reports that the three tests pass after the change. The adjacent diff screenshot shows the actual calculation and formatting edits.

Review focused on preserving the `0.05` budget and `<=` boundary, checking the narrow diff, and rerunning the tests. Later screenshots show the empty-check guard and test changes in a review view. The evidence supports Copilot-assisted repair and review; it does not establish an autonomous diagnosis service inside the project.

## Incident report

[`INCIDENT_REPORT.md`](INCIDENT_REPORT.md) contains:

- **Summary:** the gate incorrectly blocked decisions within the allowed 5% failure budget.
- **Evidence:** the 1% and 5% tests failed, the 6% test passed, and local output and Actions logs showed the same deterministic failures.
- **Root cause:** percentage points were compared with a decimal fraction.
- **Resolution:** compare `failed_checks / total_checks` directly with `MAX_FAILURE_RATE`.
- **Prevention:** retain below, at, and above-budget tests and require green CI for future changes.

This is a debugging exercise. The report documents the release decision defect; the repository provides no evidence of an actual production deployment or customer incident.

## Empty-check guard

Commit [`4f21f1f`](https://github.com/AyeFuad2/ai-ci-doctor/commit/4f21f1f) adds the explicit guard and fourth test after the original unit repair.

Before the guard, `should_deploy(0, 0)` raised `ZeroDivisionError`. The current function checks `total_checks <= 0` before division and raises:

```text
ValueError: total_checks must be greater than zero
```

This rejects both zero and negative totals in the core function. The committed regression test specifically checks zero and the error message.

The scope is limited: `describe_decision` computes its ratio before calling `should_deploy`, so `describe_decision(0, 0)` still raises `ZeroDivisionError`. The implementation also does not explicitly validate nonnegative failed counts, failed counts no greater than the total, input types, or threshold bounds. These are current limitations, not implemented safeguards.

## Setup and execution

### Prerequisites

Use Git to clone the repository and Python 3 to run it. The current CI configuration requests Python `3.14.8`; local screenshots show development with Python 3.11. The project does not declare a comprehensive supported-version matrix.

No third-party Python packages, API keys, or service configuration are required for the gate and tests. Copilot is optional for running the project.

### Clone

```bash
git clone https://github.com/AyeFuad2/ai-ci-doctor.git
cd ai-ci-doctor
```

### Run the demo

```bash
python release_gate.py
```

Expected output:

```text
0/100 checks failed (0.0%): DEPLOY
6/100 checks failed (6.0%): BLOCK
```

The demo uses these two fixed examples. It does not accept command-line arguments or read live check results.

### Run the tests

```bash
python -m unittest -v
```

If `python` is unavailable on Windows but the Python launcher is installed, use `py` in place of `python`. Run tests from the repository root so the `release_gate` module is available to the test imports.

### Call the gate directly

```python
from release_gate import describe_decision, should_deploy

assert should_deploy(1, 100) is True
assert should_deploy(5, 100) is True
assert should_deploy(6, 100) is False

# A custom 2% budget, expressed as a fraction.
assert should_deploy(3, 100, max_failure_rate=0.02) is False

print(describe_decision(5, 100))
# 5/100 checks failed (5.0%): DEPLOY
```

The custom-threshold example illustrates the existing function argument; it is not an additional committed test. `describe_decision` uses the default threshold and has no custom-budget parameter.

## Project structure

```text
ai-ci-doctor/
├── .github/
│   └── workflows/
│       └── ci.yml              # CI event triggers, Python setup, test command
├── tests/
│   ├── __init__.py             # Test package marker
│   └── test_release_gate.py    # Four unittest cases
├── INCIDENT_REPORT.md         # Unit-mismatch investigation
├── README.md                  # Project documentation
└── release_gate.py            # Decision logic, display helper, fixed demo
```

The repository also contains tracked `__pycache__` artifacts. They are Python bytecode files rather than application source and are omitted from the source-oriented tree above.

## Red-to-green results

| Stage | Local evidence | Captured CI evidence |
| --- | --- | --- |
| Original defect | Three tests; two failures at 1% and 5%. | Two red “Add failing release gate CI” runs. |
| Unit correction | Three existing tests pass after the fractional calculation repair. | Green “Fix release gate rate calculation” run. |
| Empty-check regression | Four-test run initially errors on division by zero. | The later guard run is shown in progress in one screenshot. |
| Guard added | All four tests pass. | Final screenshot shows green “Guard against empty check sets” and green unit-fix runs. |

The three commits preserve the implementation sequence: initial defect, rate correction, and empty-check safeguard. The demonstrated result is correct behavior for the tested boundary inputs and explicit rejection of zero totals in the core function. It does not claim complete production release safety.

## Lessons learned

- **Test the decision boundary.** The 0% and 6% demo cases looked correct while the below-budget and equality cases were broken.
- **Keep units consistent.** Compute and compare fractional rates; format them as percentages for people.
- **Preserve the intended policy.** The repair changed the calculation, not the tests or the 5% budget.
- **Constrain AI-assisted changes.** A specific repair request and an inspectable diff make review practical.
- **Verify locally and in CI.** Both test output and the captured Actions runs support the red-to-green result.
- **Harden after the primary repair.** An empty set needs an explicit error rather than an accidental arithmetic exception.
- **Record the cause.** The incident report connects the visible failures to the repair and future regression protection.

Source repository: [AyeFuad2/ai-ci-doctor](https://github.com/AyeFuad2/ai-ci-doctor).
