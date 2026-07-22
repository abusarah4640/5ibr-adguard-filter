from scripts.analyze import main


def run_analysis(
    domain: str,
    capsys,
) -> str:
    status = main([domain])

    assert status == 0

    return capsys.readouterr().out


def test_cli_shows_safe_to_block_policy(
    capsys,
):
    output = run_analysis(
        "tpc.googlesyndication.com",
        capsys,
    )

    assert (
        "Blocking Policy"
        in output
    )

    assert (
        "safe-to-block"
        in output
    )

    assert (
        "Policy Reason"
        in output
    )

    assert (
        "Policy Source"
        in output
    )

    assert (
        "category-policy"
        in output
    )


def test_cli_shows_needs_testing_policy(
    capsys,
):
    output = run_analysis(
        "beacons.gvt2.com",
        capsys,
    )

    assert (
        "needs-testing"
        in output
    )


def test_cli_protects_streaming_domain(
    capsys,
):
    output = run_analysis(
        "youtubei.googleapis.com",
        capsys,
    )

    assert (
        "Suggested Category : Streaming"
        in output
    )

    assert (
        "Blocking Policy"
        in output
    )

    assert (
        "do-not-block"
        in output
    )


def test_cli_keeps_legacy_fields(
    capsys,
):
    output = run_analysis(
        "beacons.gvt2.com",
        capsys,
    )

    required = (
        "Domain",
        "Root",
        "Suggested Vendor",
        "Suggested Category",
        "Suggested Filter",
        "Confidence",
        "Recommendation",
        "Reasons",
    )

    for label in required:
        assert label in output
