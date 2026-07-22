import json

from scripts.conflict_impact_report import (
    analyze_conflict_impact,
    build_report,
    has_conflict_reason,
    main,
)


def test_has_conflict_reason():
    assert has_conflict_reason(
        {
            "reasons": [
                "conflicting category evidence: "
                "rule=Telemetry, knowledge=Gaming"
            ]
        }
    )

    assert not has_conflict_reason(
        {
            "reasons": [
                "matched known vendor namespace"
            ]
        }
    )


def test_analyze_conflict_impact():
    before = [
        {
            "domain": "a.example",
            "confidence": 100,
            "recommendation": "approved-candidate",
        },
        {
            "domain": "b.example",
            "confidence": 80,
            "recommendation": "review",
        },
    ]

    after = [
        {
            "domain": "a.example",
            "confidence": 89,
            "recommendation": "review",
            "reasons": [
                "conflicting category evidence: "
                "rule=Telemetry, knowledge=Gaming"
            ],
        },
        {
            "domain": "b.example",
            "confidence": 80,
            "recommendation": "review",
            "reasons": [],
        },
    ]

    impact, changed = analyze_conflict_impact(
        before,
        after,
    )

    assert impact.common_domains == 2
    assert impact.lowered_domains == 1
    assert impact.raised_domains == 0
    assert impact.unchanged_domains == 1
    assert impact.approved_to_review == 1
    assert impact.lowered_with_conflict_reason == 1
    assert impact.lowered_without_conflict_reason == 0
    assert impact.max_drop == -11
    assert impact.max_raise == 0
    assert len(changed) == 1


def test_build_conflict_impact_report(tmp_path):
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"

    before_path.write_text(
        json.dumps(
            {
                "suggestions": [
                    {
                        "domain": "a.example",
                        "confidence": 100,
                        "recommendation": "approved-candidate",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    after_path.write_text(
        json.dumps(
            {
                "suggestions": [
                    {
                        "domain": "a.example",
                        "confidence": 89,
                        "recommendation": "review",
                        "reasons": [
                            "conflicting category evidence: "
                            "rule=Telemetry, knowledge=Gaming"
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report(
        before_path,
        after_path,
    )

    assert "5ibr Conflict Impact Report" in report
    assert "Approved -> review           : 1" in report
    assert "Lowered without conflict     : 0" in report
    assert "a.example" in report


def test_conflict_impact_cli(tmp_path, capsys):
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"

    before_path.write_text(
        json.dumps(
            {
                "suggestions": [
                    {
                        "domain": "a.example",
                        "confidence": 100,
                        "recommendation": "approved-candidate",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    after_path.write_text(
        json.dumps(
            {
                "suggestions": [
                    {
                        "domain": "a.example",
                        "confidence": 89,
                        "recommendation": "review",
                        "reasons": [
                            "conflicting filter evidence: "
                            "current=telemetry, knowledge=gaming"
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            str(before_path),
            str(after_path),
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "5ibr Conflict Impact Report" in output
    assert "Lowered with conflict reason : 1" in output
