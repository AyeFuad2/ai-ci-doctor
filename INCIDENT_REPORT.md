# Incident Report: Release Gate Unit Mismatch

## Summary

The CI release gate blocked deployments that were still within the allowed 5 percent failure budget.

## Evidence

- `test_allows_release_below_budget` failed for 1 failed check out of 100.
- `test_allows_release_at_budget` failed for 5 failed checks out of 100.
- `test_blocks_release_above_budget` passed for 6 failed checks out of 100.
- The local test output and GitHub Actions logs showed the same deterministic failures.

## Root Cause

The implementation converted the failed-check ratio into percentage points by multiplying by 100, then compared that value with `0.05`, which represents a decimal fraction.

## Resolution

The implementation now compares `failed_checks / total_checks` directly with `MAX_FAILURE_RATE`.

## Prevention

Keep boundary tests below, at, and above the configured error budget, and require a green CI run before accepting future release-gate changes.
