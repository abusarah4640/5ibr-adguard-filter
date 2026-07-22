#!/usr/bin/env python3
"""
5ibr Filter Toolkit v1.7.0 Stage 1 Safe Installer
Adds Analyzer UX helper functions safely, without restructuring create_app().
"""
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime

ROOT = Path.cwd()
APP = ROOT / "web" / "app.py"
TEST = ROOT / "tests" / "test_web_v170_safe_helpers.py"
VERSION = ROOT / "VERSION"

HELPERS = r'''

# v1.7.0 Analyzer UX helpers
UNKNOWN_VALUES = {"", "unknown", "Unknown", "UNKNOWN", "none", "None", "-", "—"}


def normalize_unknown(value, fallback=""):
    """Return an empty/fallback value for Unknown-like analyzer fields."""
    text = "" if value is None else str(value).strip()
    return fallback if text in UNKNOWN_VALUES else text


def confidence_level(value):
    """Return Bootstrap-like confidence level name."""
    try:
        score = int(value or 0)
    except (TypeError, ValueError):
        score = 0
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def recommendation_badge(value):
    """Return a UI badge class name for analyzer recommendation."""
    text = ("" if value is None else str(value).strip().lower())
    if text in {"approved", "approved-candidate"}:
        return "success"
    if text == "review":
        return "warning"
    if text in {"rejected", "reject"}:
        return "danger"
    return "secondary"


def explain_suggestion(row):
    """Build a small explanation model for a suggestion row."""
    row = row or {}
    reasons_raw = row.get("Reasons", "") or row.get("reasons", "") or ""
    reasons = [item.strip() for item in str(reasons_raw).replace(";", "\n").splitlines() if item.strip()]
    if not reasons:
        reasons = ["No local analyzer rules matched"]
    return {
        "domain": row.get("Domain") or row.get("domain") or "",
        "root": row.get("Root") or row.get("root") or "",
        "vendor": normalize_unknown(row.get("Suggested Vendor") or row.get("Vendor"), "Needs selection"),
        "category": normalize_unknown(row.get("Suggested Category") or row.get("Category"), "Needs selection"),
        "filter": normalize_unknown(row.get("Suggested Filter") or row.get("Filter"), "Needs selection"),
        "confidence": row.get("Confidence") or row.get("confidence") or 0,
        "recommendation": row.get("Recommendation") or row.get("recommendation") or "unknown",
        "reasons": reasons,
    }
'''

GLOBALS_BLOCK = '''        app.jinja_env.globals.update(
            normalize_unknown=normalize_unknown,
            confidence_level=confidence_level,
            recommendation_badge=recommendation_badge,
            explain_suggestion=explain_suggestion,
        )
'''

TEST_CODE = r'''import web.app as webapp


def test_v170_safe_helpers_exist():
    assert webapp.normalize_unknown("Unknown") == ""
    assert webapp.normalize_unknown("unknown", "Needs selection") == "Needs selection"
    assert webapp.normalize_unknown("Google") == "Google"
    assert webapp.confidence_level(90) == "high"
    assert webapp.confidence_level(60) == "medium"
    assert webapp.confidence_level(10) == "low"
    assert webapp.recommendation_badge("review") == "warning"
    assert webapp.recommendation_badge("approved-candidate") == "success"


def test_v170_helpers_registered_in_jinja():
    app = webapp.app
    assert "normalize_unknown" in app.jinja_env.globals
    assert "confidence_level" in app.jinja_env.globals
    assert "recommendation_badge" in app.jinja_env.globals
    assert "explain_suggestion" in app.jinja_env.globals
'''


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main():
    if not APP.exists():
        raise SystemExit("ERROR: web/app.py not found. Run from /opt/5ibr")

    # Preflight: current app must compile before editing.
    pre = run([sys.executable, "-m", "py_compile", str(APP)])
    if pre.returncode != 0:
        print(pre.stdout)
        raise SystemExit("ERROR: current web/app.py does not compile. Restore clean v1.6.4 first.")

    backup_dir = ROOT / ".v170_stage1_backup"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (backup_dir / f"app.py.{stamp}").write_text(APP.read_text(encoding="utf-8"), encoding="utf-8")

    s = APP.read_text(encoding="utf-8")

    if "def normalize_unknown(" not in s:
        idx = s.find("def create_app()")
        if idx == -1:
            raise SystemExit("ERROR: def create_app() not found")
        s = s[:idx] + HELPERS + "\n" + s[idx:]

    if "normalize_unknown=normalize_unknown" not in s:
        # Insert directly after the app = Flask(__name__) line inside create_app.
        pattern = r'(?m)^(\s*)app\s*=\s*Flask\(__name__\)\s*$'
        m = re.search(pattern, s)
        if not m:
            raise SystemExit("ERROR: app = Flask(__name__) line not found")
        line_end = s.find("\n", m.end())
        if line_end == -1:
            line_end = len(s)
        s = s[:line_end + 1] + GLOBALS_BLOCK + s[line_end + 1:]

    APP.write_text(s, encoding="utf-8")
    VERSION.write_text("1.7.0-stage1\n", encoding="utf-8")
    TEST.write_text(TEST_CODE, encoding="utf-8")

    post = run([sys.executable, "-m", "py_compile", str(APP)])
    if post.returncode != 0:
        print(post.stdout)
        # restore
        latest = sorted(backup_dir.glob("app.py.*"))[-1]
        APP.write_text(latest.read_text(encoding="utf-8"), encoding="utf-8")
        raise SystemExit("ERROR: compile failed; restored previous web/app.py")

    print("OK: v1.7.0 stage1 helpers installed safely")
    print("Next: pytest -q")


if __name__ == "__main__":
    main()
