#!/usr/bin/env python3
"""
5ibr v1.6.4 fix1 - Review Queue one-click approval safety fix.
Run from /opt/5ibr:
    python fix_v1.6.4_review_queue.py
"""
from pathlib import Path
import re

APP = Path("web/app.py")
if not APP.exists():
    raise SystemExit("web/app.py not found. Run this script from /opt/5ibr")

s = APP.read_text(encoding="utf-8")

# Ensure subprocess helper import/runtime helper exists.
if "def run_fivebr(" not in s:
    # subprocess is imported inside helper to avoid needing top-level import.
    helper = '''\n\ndef run_fivebr(*args):\n    import subprocess\n    proc = subprocess.run(\n        ["fivebr", *args],\n        cwd=BASE_DIR,\n        text=True,\n        stdout=subprocess.PIPE,\n        stderr=subprocess.STDOUT,\n        check=False,\n    )\n    return proc.returncode, proc.stdout\n'''
    marker = "\napp = Flask(__name__)"
    if marker in s:
        s = s.replace(marker, helper + marker, 1)
    else:
        s += helper

# Add a restore helper. It writes to the current suggestions_service.SUGGESTIONS_CSV,
# so pytest monkeypatches are respected.
restore_helper = '''\n\ndef restore_suggestion_if_missing(suggestion):\n    import csv\n    import scripts.services.suggestions_service as svc\n\n    fieldnames = [\n        "Domain", "Seen", "Root", "Suggested Vendor",\n        "Suggested Category", "Suggested Filter",\n        "Confidence", "Recommendation", "Reasons",\n    ]\n    domain = (suggestion.get("Domain", "") or "").strip()\n    if not domain:\n        return\n\n    path = svc.SUGGESTIONS_CSV\n    text = path.read_text(encoding="utf-8") if path.exists() else ""\n    if domain in text:\n        return\n\n    path.parent.mkdir(parents=True, exist_ok=True)\n    with path.open("a", newline="", encoding="utf-8") as fh:\n        writer = csv.DictWriter(fh, fieldnames=fieldnames)\n        if not text:\n            writer.writeheader()\n        writer.writerow({key: suggestion.get(key, "") for key in fieldnames})\n'''

if "def restore_suggestion_if_missing(" not in s:
    marker = "\napp = Flask(__name__)"
    if marker in s:
        s = s.replace(marker, restore_helper + marker, 1)
    else:
        s += restore_helper

new_func = '''    @app.route("/review-queue/<path:domain>/<action>", methods=["POST"])
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
                append_decision(suggestion, "approved-failed", "; ".join(errors) or reason)
                restore_suggestion_if_missing(suggestion)
                for error in errors:
                    flash(error, "danger")
                log_event("review_queue.approved", domain, "error", "; ".join(errors))
                return redirect(request.form.get("next") or url_for("review_queue"))

            code, output = run_fivebr("build")
            if code != 0:
                append_decision(suggestion, "approved-build-failed", output or reason)
                restore_suggestion_if_missing(suggestion)
                log_event("review_queue.build", domain, "error", output)
                flash("Domain was added, but build failed. Suggestion was kept for review.", "danger")
                return redirect(request.form.get("next") or url_for("review_queue"))

            remove_suggestion(domain)
            append_decision(suggestion, action, reason)
            log_event("review_queue.approved", domain, "ok", output)
            flash("Suggestion approved, added to database, and filters rebuilt.", "success")
            return redirect(request.form.get("next") or url_for("review_queue"))

        # Review decisions only mark the row; they do not remove it from the queue file.
        append_decision(suggestion, action, reason)
        log_event(f"review_queue.{action}", domain, "ok", reason)
        flash("Review decision saved.", "success")
        return redirect(request.form.get("next") or url_for("review_queue"))

'''

pattern = (
    r'    @app\.route\("/review-queue/<path:domain>/<action>", methods=\["POST"\]\)\n'
    r'    def review_queue_action\(domain: str, action: str\):.*?\n'
    r'    @app\.route\("/reports/suggestions"\)'
)

s2, n = re.subn(pattern, new_func + '    @app.route("/reports/suggestions")', s, flags=re.S)
if n != 1:
    raise SystemExit(f"Could not replace review_queue_action cleanly. matches={n}")

APP.write_text(s2, encoding="utf-8")
print("OK: v1.6.4 Review Queue fix1 applied")
