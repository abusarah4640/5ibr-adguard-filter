import json
from pathlib import Path

from scripts.confidence_impact_report import (
    analyze_impact,
    build_report,
    main,
)


def test_analyze_confidence_impact():
    before = [
        {"domain": "a.example", "confidence": 20, "seen": 10},
        {"domain": "b.example", "confidence": 50, "seen": 20},
        {"domain": "c.example", "confidence": 90, "seen": 30},
    ]

    after = [
        {
            "domain": "a.example",
            "confidence": 50,
            "seen": 10,
            "vendor": "A",
            "category": "X",
            "filter": "x",
        },
        {
            "domain": "b.example",
            "confidence": 80,
            "seen": 20,
            "vendor": "B",
            "category": "Y",
            "filter": "y",
        },
        {
            "domain": "c.example",
            "confidence": 90,
            "seen": 30,
            "vendor": "C",
            "category": "Z",
            "filter": "z",
        },
    ]

    impact, changed = analyze_impact(before, after)

    assert impact.total_common == 3
    assert impact.moved_to_review == 1
    assert impact.moved_to_approved == 0
    assert impact.decreased_below_review == 0
    assert impact.unchanged == 1
    assert impact.average_before == 160 / 3
    assert impact.average_after == 220 / 3
    assert impact.max_increase == 30
    assert impact.max_decrease == 0
    assert len(changed) == 2


def test_build_confidence_impact_report(tmp_path):
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"

    before_path.write_text(
        json.dumps(
            {
                "suggestions": [
                    {
                        "domain": "a.example",
                        "confidence": 20,
                        "seen": 10,
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
                        "confidence": 50,
                        "seen": 10,
                        "vendor": "A",
                        "category": "X",
                        "filter": "x",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report(before_path, after_path)

    assert "5ibr Confidence Impact Report" in report
    assert "Moved to review      : 1" in report
    assert "a.example" in report


def test_confidence_impact_cli(tmp_path, capsys):
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"

    payload = {
        "suggestions": [
            {
                "domain": "a.example",
                "confidence": 20,
                "seen": 10,
            }
        ]
    }

    before_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    payload["suggestions"][0]["confidence"] = 50

    after_path.write_text(
        json.dumps(payload),
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
    assert "5ibr Confidence Impact Report" in output
