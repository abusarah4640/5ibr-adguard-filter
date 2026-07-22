from pathlib import Path

p = Path("web/app.py")
s = p.read_text(encoding="utf-8")

start = s.index('    @app.route("/review-queue/<path:domain>/<action>", methods=["POST"])')
end = s.index('    @app.route("/reports/suggestions")', start)

new_block = r'''    @app.route("/review-queue/<path:domain>/<action>", methods=["POST"])
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
                log_event("review_queue.approved", domain, "error", "; ".join(errors))
                return redirect(request.form.get("next") or url_for("review_queue"))

            code, output = run_fivebr("build")

            if code != 0:
                # Important: keep the suggestion visible if build fails.
                log_event("review_queue.build", domain, "error", output)
                flash("Domain was added, but build failed. Suggestion was kept for review.", "danger")
                return redirect(request.form.get("next") or url_for("review_queue"))

            remove_suggestion(domain)
            append_decision(suggestion, action, reason)
            log_event("review_queue.approved", domain, "ok", output)
            flash("Suggestion approved, added to database, and filters rebuilt.", "success")
            return redirect(request.form.get("next") or url_for("review_queue"))

        append_decision(suggestion, action, reason)
        log_event(f"review_queue.{action}", domain, "ok", reason)
        flash("Review decision saved.", "success")
        return redirect(request.form.get("next") or url_for("review_queue"))

'''

p.write_text(s[:start] + new_block + s[end:], encoding="utf-8")
print("OK: replaced review_queue_action")
