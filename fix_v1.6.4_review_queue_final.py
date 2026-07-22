#!/usr/bin/env python3
"""Fix v1.6.4 Review Queue one-click approval.

This repair addresses the case where pytest monkeypatches web.app.run_fivebr,
but the route still calls a nested/local run_fivebr function. It also hardens
suggestion deletion so suggestions are removed only after a successful build.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd()
APP = ROOT / "web" / "app.py"
SVC = ROOT / "scripts" / "services" / "suggestions_service.py"


def fail(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")

if not APP.exists():
    fail("web/app.py not found. Run this from /opt/5ibr")
if not SVC.exists():
    fail("scripts/services/suggestions_service.py not found. Run this from /opt/5ibr")

app = APP.read_text(encoding="utf-8")

# Ensure subprocess/sys imports are present for the module-level helper.
if "import subprocess" not in app:
    app = app.replace("from __future__ import annotations\n", "from __future__ import annotations\n\nimport subprocess\n", 1)
if "import sys" not in app:
    if "import subprocess\n" in app:
        app = app.replace("import subprocess\n", "import subprocess\nimport sys\n", 1)
    else:
        app = app.replace("from __future__ import annotations\n", "from __future__ import annotations\n\nimport sys\n", 1)

# Ensure module-level BASE_DIR/ROOT compatibility and run_fivebr helper.
# Some versions use ROOT, some use BASE_DIR. We preserve both.
if "BASE_DIR = Path(__file__).resolve().parent.parent" not in app:
    if "ROOT = Path(__file__).resolve().parent.parent" in app:
        app = app.replace(
            "ROOT = Path(__file__).resolve().parent.parent",
            "ROOT = Path(__file__).resolve().parent.parent\nBASE_DIR = ROOT",
            1,
        )
    else:
        marker = "from web.i18n"
        idx = app.find(marker)
        if idx != -1:
            line_end = app.find("\n", idx)
            app = app[: line_end + 1] + "\nBASE_DIR = Path(__file__).resolve().parent.parent\nROOT = BASE_DIR\n" + app[line_end + 1 :]

if not re.search(r"^def run_fivebr\(", app, flags=re.M):
    # Put module-level helper before create_app(), so tests can monkeypatch web.app.run_fivebr.
    m = re.search(r"\ndef create_app\(\) -> Flask:\n", app)
    if not m:
        fail("Could not find create_app() in web/app.py")
    helper = '''\n\ndef run_fivebr(*args: str) -> tuple[int, str]:\n    """Run the fivebr CLI. Kept module-level so tests and routes can monkeypatch it."""\n    root = globals().get("BASE_DIR", globals().get("ROOT", Path(__file__).resolve().parent.parent))\n    cmd_file = Path(root) / "fivebr.py"\n    if cmd_file.exists():\n        cmd = [sys.executable, str(cmd_file), *args]\n    else:\n        cmd = ["fivebr", *args]\n    proc = subprocess.run(\n        cmd,\n        cwd=root,\n        text=True,\n        stdout=subprocess.PIPE,\n        stderr=subprocess.STDOUT,\n        check=False,\n    )\n    return proc.returncode, proc.stdout or ""\n'''
    app = app[: m.start()] + helper + app[m.start():]

# Replace the review_queue_action route with a clean implementation that explicitly calls
# the module-level run_fivebr via globals(), bypassing any nested helper closure.
route_pattern = re.compile(
    r'    @app\.route\("/review-queue/<path:domain>/<action>", methods=\["POST"\]\)\n'
    r'    def review_queue_action\(domain: str, action: str\):.*?'
    r'(?=    @app\.route\("/reports/suggestions"\))',
    flags=re.S,
)
new_route = '''    @app.route("/review-queue/<path:domain>/<action>", methods=["POST"])
    def review_queue_action(domain: str, action: str):
        allowed = {"approved", "rejected", "ignored"}
        if action not in allowed:
            flash("Invalid review action.", "danger")
            return redirect(url_for("review_queue"))

        suggestion = find_suggestion(domain)
        if not suggestion:
            flash("Suggestion not found.", "danger")
            return redirect(url_for("review_queue"))

        reason = request.form.get("reason", "").strip()

        if action == "approved":
            create_backup("review-queue-approve")

            ok, errors = add_validated_domain(
                domain=suggestion.get("Domain", ""),
                vendor=suggestion.get("Suggested Vendor", ""),
                category=suggestion.get("Suggested Category", ""),
                filter_name=suggestion.get("Suggested Filter", ""),
                confidence=to_int(suggestion.get("Confidence"), 0),
                status="Approved",
                source="review-queue",
                evidence=f"Seen {suggestion.get('Seen', '')} times; {suggestion.get('Reasons', '')}",
                notes=reason or "Approved from Review Queue",
                reviewer="web-ui",
            )

            if not ok:
                for error in errors:
                    flash(error, "danger")
                append_decision(suggestion, "approved-failed", "; ".join(errors) or reason)
                log_event("review_queue.approved", domain, "error", "; ".join(errors))
                return redirect(request.form.get("next") or url_for("review_queue"))

            # IMPORTANT: use module-level run_fivebr so pytest monkeypatching web.app.run_fivebr works.
            code, output = globals()["run_fivebr"]("build")

            if code != 0:
                append_decision(suggestion, "approved-build-failed", output or reason)
                log_event("review_queue.build", domain, "error", output)
                flash("Domain was added, but build failed. Suggestion was kept for review.", "danger")
                return redirect(request.form.get("next") or url_for("review_queue"))

            remove_suggestion(domain)
            append_decision(suggestion, action, reason)
            log_event("review_queue.approved", domain, "ok", output)
            flash("Suggestion approved, added to database, and filters rebuilt.", "success")
            return redirect(request.form.get("next") or url_for("review_queue"))

        # Review-only actions are intentionally non-destructive.
        append_decision(suggestion, action, reason)
        log_event(f"review_queue.{action}", domain, "ok", reason)
        flash("Review decision saved.", "success")
        return redirect(request.form.get("next") or url_for("review_queue"))

'''
app2, count = route_pattern.subn(new_route, app)
if count != 1:
    fail(f"Could not replace review_queue_action route. matches={count}")
APP.write_text(app2, encoding="utf-8")

# Harden suggestions_service: append_decision must be non-destructive. If an older broken
# copy still removes suggestions in append_decision, strip those calls from the function body.
svc = SVC.read_text(encoding="utf-8")
if "def append_decision" in svc:
    start = svc.index("def append_decision")
    next_func = svc.find("\ndef ", start + 1)
    if next_func == -1:
        next_func = len(svc)
    body = svc[start:next_func]
    body = re.sub(r"\n\s*remove_suggestion\([^\n]*\)", "", body)
    body = re.sub(r"\n\s*if action not in \{[^\n]*\}:\n\s*remove_suggestion\([^\n]*\)", "", body)
    svc = svc[:start] + body + svc[next_func:]
SVC.write_text(svc, encoding="utf-8")

print("OK: v1.6.4 Review Queue fixed")
print("Next: pytest -q")
