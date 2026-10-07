MAX_FAILURE_RATE = 0.05


def should_deploy(failed_checks, total_checks, max_failure_rate=MAX_FAILURE_RATE):
    if total_checks <= 0:
        raise ValueError("total_checks must be greater than zero")

    failure_rate = failed_checks / total_checks
    return failure_rate <= max_failure_rate


def describe_decision(failed_checks, total_checks):
    failure_rate = failed_checks / total_checks
    decision = "DEPLOY" if should_deploy(failed_checks, total_checks) else "BLOCK"
    return (
        f"{failed_checks}/{total_checks} checks failed "
        f"({failure_rate:.1%}): {decision}"
    )


def main():
    for failed_checks, total_checks in ((0, 100), (6, 100)):
        print(describe_decision(failed_checks, total_checks))


if __name__ == "__main__":
    main()