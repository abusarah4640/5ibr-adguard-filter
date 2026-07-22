#!/usr/bin/env python3
"""Small Flask admin UI for the 5ibr AdGuard Filter Toolkit."""

from __future__ import annotations

from scripts.runtime.paths import (
    get_runtime_paths,
)
from scripts.version import (
    get_version,
)
from scripts.services.intelligence_summary_service import build_intelligence_summary
from scripts.services.intelligence_diagnostics_service import build_intelligence_diagnostics
from scripts.services.guardrail_readiness_service import (
    load_enforcement_readiness,
)
from scripts.services.readiness_history_service import (
    append_readiness_snapshot,
    load_readiness_history_summary,
)
from scripts.services.readiness_decision_service import (
    evaluate_readiness_decision,
)
from scripts.services.readiness_approval_service import (
    CONFIRMATION_PHRASE,
    latest_matching_approval,
    record_manual_readiness_approval,
)
from scripts.services.readiness_audit_archive_service import (
    archive_manual_readiness_approval,
    archive_readiness_decision,
    load_readiness_audit_archive_summary,
)

import subprocess
import sys
import os
import re
import secrets
import time
from functools import wraps
from zoneinfo import available_timezones
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from flask import Flask, flash, make_response, redirect, render_template, request, send_from_directory, session, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user

from scripts.database import load_database, remove_domain, search_domain
from scripts.services.audit_service import log_event, recent_events
from scripts.services.backup_service import create_backup
from scripts.services.database_service import add_validated_domain, update_validated_domain
from scripts.services.suggestions_service import append_decision, append_rejected, find_suggestion, load_review_queue, load_suggestions, remove_suggestion
from web.auth import UserStore
from web.dashboard_analytics import (
    audit_operation_key, display_events, domain_analytics, format_display_datetime,
    operational_activity, readiness_display_state, readiness_next_action,
)
from web.i18n import (
    direction, get_lang, translate, translate_category, translate_confidence,
    translate_decision, translate_dynamic_text, translate_guardrail, translate_recommendation,
    translate_status, translate_vendor,
)

RUNTIME_PATHS = get_runtime_paths()

ROOT = RUNTIME_PATHS.root
BASE_DIR = RUNTIME_PATHS.root
RELEASES_DIR = RUNTIME_PATHS.releases
REPORTS_DIR = RUNTIME_PATHS.reports
UPLOADS_DIR = (
    RUNTIME_PATHS.data
    / "uploads"
)
VERSION_FILE = RUNTIME_PATHS.version_file


def read_version() -> str:
    """Return the installed package version."""

    try:
        value = get_version()
    except Exception:
        value = ""

    return value.strip() or "unknown"




def human_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def human_mtime(timestamp: float) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def database_options() -> dict[str, list[str]]:
    rows = load_database()
    return {
        "vendors": sorted({row.get("Vendor", "") for row in rows if row.get("Vendor", "")}),
        "categories": sorted({row.get("Category", "") for row in rows if row.get("Category", "")}),
        "filters": sorted({row.get("Filter", "") for row in rows if row.get("Filter", "")}),
    }



def to_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value or '').strip())
    except (TypeError, ValueError):
        return default


def suggestion_analysis(rows: list[dict[str, str]]) -> dict[str, object]:
    total = len(rows)
    confidence_values = [to_int(row.get('Confidence')) for row in rows]
    review_count = sum(1 for row in rows if row.get('Recommendation') == 'review')
    unknown_count = sum(1 for row in rows if row.get('Recommendation') == 'unknown')
    high_confidence = sum(1 for value in confidence_values if value >= 70)
    avg_confidence = round(sum(confidence_values) / total, 1) if total else 0

    return {
        'total': total,
        'review_count': review_count,
        'unknown_count': unknown_count,
        'high_confidence': high_confidence,
        'avg_confidence': avg_confidence,
        'vendors': Counter(row.get('Suggested Vendor') or 'Unknown' for row in rows).most_common(10),
        'categories': Counter(row.get('Suggested Category') or 'Unknown' for row in rows).most_common(10),
        'recommendations': Counter(row.get('Recommendation') or 'unknown' for row in rows).most_common(10),
        'filters': Counter(row.get('Suggested Filter') or 'unknown' for row in rows).most_common(10),
    }


def suggestion_options(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    return {
        'vendors': sorted({row.get('Suggested Vendor', '') for row in rows if row.get('Suggested Vendor', '')}),
        'categories': sorted({row.get('Suggested Category', '') for row in rows if row.get('Suggested Category', '')}),
        'filters': sorted({row.get('Suggested Filter', '') for row in rows if row.get('Suggested Filter', '')}),
        'recommendations': sorted({row.get('Recommendation', '') for row in rows if row.get('Recommendation', '')}),
    }


def filter_suggestion_rows(rows: list[dict[str, str]], args) -> list[dict[str, str]]:
    query = args.get('q', '').strip().lower()
    vendor = args.get('vendor', '').strip()
    category = args.get('category', '').strip()
    filter_name = args.get('filter', '').strip()
    recommendation = args.get('recommendation', '').strip()
    min_confidence = to_int(args.get('min_confidence'), 0)

    if query:
        rows = [
            row for row in rows
            if query in row.get('Domain', '').lower()
            or query in row.get('Root', '').lower()
            or query in row.get('Suggested Vendor', '').lower()
            or query in row.get('Suggested Category', '').lower()
            or query in row.get('Suggested Filter', '').lower()
            or query in row.get('Recommendation', '').lower()
        ]
    if vendor:
        rows = [row for row in rows if row.get('Suggested Vendor') == vendor]
    if category:
        rows = [row for row in rows if row.get('Suggested Category') == category]
    if filter_name:
        rows = [row for row in rows if row.get('Suggested Filter') == filter_name]
    if recommendation:
        rows = [row for row in rows if row.get('Recommendation') == recommendation]
    if min_confidence:
        rows = [row for row in rows if to_int(row.get('Confidence')) >= min_confidence]

    sort = args.get('sort', 'seen').strip()
    reverse = args.get('direction', 'desc') != 'asc'
    if sort == 'confidence':
        rows = sorted(rows, key=lambda row: to_int(row.get('Confidence')), reverse=reverse)
    elif sort == 'domain':
        rows = sorted(rows, key=lambda row: row.get('Domain', ''), reverse=reverse)
    else:
        rows = sorted(rows, key=lambda row: to_int(row.get('Seen')), reverse=reverse)
    return rows


def review_queue_stats(rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        "total": len(rows),
        "pending": sum(1 for row in rows if row.get("Review Status", "pending") == "pending"),
        "approved": sum(1 for row in rows if row.get("Review Status") == "approved"),
        "rejected": sum(1 for row in rows if row.get("Review Status") == "rejected"),
        "ignored": sum(1 for row in rows if row.get("Review Status") == "ignored"),
        "avg_confidence": suggestion_analysis(rows)["avg_confidence"],
    }


def filter_review_queue_rows(rows: list[dict[str, str]], args) -> list[dict[str, str]]:
    rows = filter_suggestion_rows(rows, args)
    status = args.get("status", "").strip()
    if status:
        rows = [row for row in rows if row.get("Review Status", "pending") == status]
    return rows

def release_rows() -> list[dict[str, str]]:
    if not RELEASES_DIR.exists():
        return []
    rows = []
    for file in sorted(RELEASES_DIR.glob("*.txt")):
        stat = file.stat()
        rows.append({
            "name": file.name,
            "size": human_size(stat.st_size),
            "modified": human_mtime(stat.st_mtime),
            "mtime": stat.st_mtime,
        })
    return rows


def project_health(rows: list[dict], releases: list[dict]) -> tuple[str, str, str]:
    if not rows:
        return "Warning", "⚠️", "database_empty"
    if not releases:
        return "Warning", "⚠️", "no_release_files"
    return "Healthy", "🟢", "core_files_present"


def normalize_unknown(value: object, fallback: str = "") -> str:
    """Return a presentation-safe value for analyzer fields."""
    text = str(value or "").strip()
    if text.lower() in {"unknown", "none", "null", "-", "—"}:
        return fallback
    return text


def confidence_level(value: object) -> str:
    """Map a numeric confidence value to its display band."""
    try:
        score = int(value or 0)
    except (TypeError, ValueError):
        score = 0
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def recommendation_badge(value: object) -> str:
    """Return the Bootstrap badge class for a recommendation value."""
    text = str(value or "unknown").strip().lower()
    if text == "approved-candidate":
        return "success"
    if text == "review":
        return "warning"
    if text in {"rejected", "reject"}:
        return "danger"
    return "secondary"


def explain_suggestion(row: object) -> list[str]:
    """Split analyzer reasons into displayable explanation lines."""
    reasons = str(row.get("Reasons", "") if isinstance(row, dict) else "").strip()
    if not reasons:
        reasons = "No analyzer reasons available"
    return [part.strip() for part in reasons.replace(";", "\n").split("\n") if part.strip()]


def create_app(test_config: dict[str, object] | None = None) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)
    production = os.environ.get("FIVEBR_ENV", "development").lower() == "production"
    configured_secret = os.environ.get("FIVEBR_SECRET_KEY")
    if production and not configured_secret:
        raise RuntimeError("FIVEBR_SECRET_KEY is required when FIVEBR_ENV=production")
    app.config["SECRET_KEY"] = configured_secret or secrets.token_hex(32)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        minutes=int(os.environ.get("FIVEBR_SESSION_TIMEOUT_MINUTES", "30"))
    )
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_DURATION=timedelta(days=30),
        SESSION_COOKIE_SECURE=production and os.environ.get("FIVEBR_COOKIE_SECURE", "true").lower() != "false",
        REMEMBER_COOKIE_SECURE=production and os.environ.get("FIVEBR_COOKIE_SECURE", "true").lower() != "false",
        SESSION_COOKIE_NAME="fivebr_session",
        REMEMBER_COOKIE_NAME="fivebr_remember",
        CSRF_ENABLED=True,
        TRUSTED_HOSTS=[host.strip() for host in os.environ.get("FIVEBR_TRUSTED_HOSTS", "").split(",") if host.strip()] or None,
    )
    if test_config:
        app.config.update(test_config)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    users = UserStore(Path(app.config.get("USER_DATABASE", RUNTIME_PATHS.data / "web_users.sqlite3")))
    users.initialize()
    app.extensions["fivebr_users"] = users
    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return users.get(user_id)

    @login_manager.unauthorized_handler
    def unauthorized():
        flash(translate("login_required"), "warning")
        return redirect(url_for("login", next=request.full_path))

    def roles_required(*roles: str):
        """Require authentication and one of the supplied roles; fail closed."""
        def decorate(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                if app.testing and not app.config.get("SECURITY_TESTING"):
                    return view(*args, **kwargs)
                if not current_user.is_authenticated:
                    return login_manager.unauthorized()
                if not current_user.has_role(*roles):
                    return (translate("forbidden"), 403)
                return view(*args, **kwargs)
            return wrapped
        return decorate

    def safe_next(target: str | None, fallback: str) -> str:
        target = (target or "").strip()
        if target.startswith("/") and not target.startswith("//") and "\\" not in target:
            return target
        return fallback

    def csrf_token() -> str:
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    @app.before_request
    def refresh_session() -> None:
        session.permanent = True
        if request.args.get("lang") in {"en", "ar"}:
            session["language"] = request.args["lang"]

    @app.before_request
    def verify_csrf():
        if request.method != "POST" or not app.config.get("CSRF_ENABLED", True):
            return None
        if app.testing and not app.config.get("SECURITY_TESTING"):
            return None
        if not current_user.is_authenticated and request.endpoint != "login":
            fallback = url_for("dashboard")
            parsed = urlsplit(request.referrer or "")
            if parsed.netloc == request.host and parsed.scheme in {"http", "https"}:
                fallback = safe_next(
                    parsed.path + (f"?{parsed.query}" if parsed.query else ""),
                    fallback,
                )
            flash(translate("login_required"), "warning")
            return redirect(url_for("login", next=fallback))
        expected = session.get("_csrf_token", "")
        supplied = request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            return (translate("csrf_failed"), 400)
        return None

    @app.context_processor
    def inject_i18n():
        lang = get_lang()
        return {
            "t": translate,
            "current_lang": lang,
            "html_dir": direction(lang),
            "other_lang": "ar" if lang == "en" else "en",
            "translate_status": translate_status,
            "translate_category": translate_category,
            "translate_vendor": translate_vendor,
            "translate_recommendation": translate_recommendation,
            "translate_guardrail": translate_guardrail,
            "translate_confidence": translate_confidence,
            "translate_decision": translate_decision,
            "translate_dynamic_text": translate_dynamic_text,
            "csrf_token": csrf_token,
            "runtime_version": read_version(),
            "runtime_environment": os.environ.get("FIVEBR_ENV", "production" if production else "development"),
            "runtime_commit": os.environ.get("FIVEBR_COMMIT", "local"),
        }

    @app.after_request
    def inject_csrf_fields(response):
        """Add a synchronizer token to every rendered POST form centrally."""
        if response.mimetype == "text/html" and response.status_code < 400:
            body = response.get_data(as_text=True)
            hidden = f'<input type="hidden" name="csrf_token" value="{csrf_token()}">'
            pattern = re.compile(r"(<form\b(?=[^>]*\bmethod=[\"']post[\"'])[^>]*>)", re.IGNORECASE)
            body = pattern.sub(lambda match: match.group(1) + hidden, body)
            response.set_data(body)
        return response

    @app.route("/language/<lang>")
    def set_language(lang: str):
        if lang not in {"en", "ar"}:
            lang = "en"
        session["language"] = lang
        if current_user.is_authenticated:
            users.update_profile(current_user.id, language=lang)
        response = make_response(redirect(safe_next(request.args.get("next"), url_for("dashboard"))))
        response.set_cookie(
            "fivebr_lang", lang, max_age=60 * 60 * 24 * 365,
            samesite="Lax", secure=bool(app.config["SESSION_COOKIE_SECURE"]),
        )
        return response

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            user = users.authenticate(request.form.get("username", ""), request.form.get("password", ""))
            if user:
                login_user(user, remember=request.form.get("remember") == "on")
                session["language"] = user.language
                flash(translate("login_success"), "success")
                return redirect(safe_next(request.args.get("next"), url_for("dashboard")))
            flash(translate("login_failed"), "danger")
        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        flash(translate("logout_success"), "success")
        return redirect(url_for("login"))

    @app.route("/settings", methods=["GET", "POST"])
    @login_required
    def settings():
        if request.method == "POST":
            language = request.form.get("language", "en")
            theme = request.form.get("theme", "auto")
            date_format = request.form.get("date_format", "yyyy-mm-dd")
            timezone = request.form.get("timezone", "UTC").strip() or "UTC"
            email = request.form.get("email", "").strip()
            display_name = request.form.get("display_name", "").strip()
            if (
                language not in {"en", "ar"}
                or theme not in {"light", "dark", "auto"}
                or date_format not in {"yyyy-mm-dd", "dd/mm/yyyy", "mm/dd/yyyy"}
                or timezone not in (available_timezones() | {"UTC", "Asia/Riyadh"})
                or len(email) > 254
                or len(display_name) > 120
            ):
                return ("Invalid settings", 400)
            users.update_profile(
                current_user.id,
                display_name=display_name,
                email=email,
                language=language, theme=theme,
                timezone=timezone,
                date_format=date_format,
            )
            session["language"] = language
            flash(translate("settings_saved"), "success")
            return redirect(url_for("settings"))
        return render_template("settings.html")

    @app.route("/settings/password", methods=["POST"])
    @login_required
    def change_password():
        new_password = request.form.get("new_password", "")
        if new_password != request.form.get("confirm_password", ""):
            flash(translate("password_mismatch"), "danger")
        else:
            try:
                changed = users.change_password(current_user.id, request.form.get("current_password", ""), new_password)
            except ValueError as exc:
                flash(str(exc), "danger")
            else:
                flash(translate("password_changed" if changed else "current_password_invalid"), "success" if changed else "danger")
        return redirect(url_for("settings"))

    def run_fivebr(*args: str) -> tuple[int, str]:
        result = subprocess.run(
            [sys.executable, "-m", "fivebr", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode, output.strip()

    @app.route("/")
    @roles_required("admin", "editor", "viewer")
    def dashboard() -> str:
        rows = load_database()
        releases = release_rows()
        suggestions = load_suggestions()
        approved = sum(1 for row in rows if (row.get("Status") or "Approved") == "Approved")
        pending = sum(1 for row in rows if (row.get("Status") or "Approved") != "Approved")
        last_build = max((file["mtime"] for file in releases), default=0)
        health_status, health_icon, health_note = project_health(rows, releases)
        intelligence = build_intelligence_summary()
        raw_audit_events = recent_events(500)
        visible_audit_events = display_events(raw_audit_events, testing=app.testing)
        analytics = domain_analytics(rows)

        try:
            readiness = load_enforcement_readiness()
        except Exception:
            readiness = None

        readiness_history = None
        readiness_decision = None
        readiness_approval = None
        readiness_audit_archive = None
        if readiness is not None:
            try:
                append_readiness_snapshot(readiness)
                readiness_history = load_readiness_history_summary()
                readiness_decision = evaluate_readiness_decision(
                    readiness,
                    readiness_history.entries,
                )
                readiness_approval = latest_matching_approval(readiness_decision)
                archive_readiness_decision(readiness_decision)
                readiness_audit_archive = load_readiness_audit_archive_summary()
            except Exception:
                readiness_history = None
                readiness_decision = None
                readiness_audit_archive = None

        display_state = readiness_display_state(readiness)
        return render_template(
            "dashboard.html",
            rows=rows,
            domain_count=len(rows),
            approved=approved,
            pending=pending,
            releases=releases,
            suggestions_count=len(suggestions),
            audit_events=visible_audit_events[:8],
            operational_activity=operational_activity(raw_audit_events, testing=app.testing),
            domain_analytics=analytics,
            last_build_text=human_mtime(last_build),
            version=read_version(),
            health_status=health_status,
            health_icon=health_icon,
            health_note=health_note,
            intelligence=intelligence,
            readiness=readiness,
            readiness_display_state=display_state,
            readiness_next_action=readiness_next_action(readiness, display_state),
            readiness_history=readiness_history,
            readiness_decision=readiness_decision,
            readiness_approval=readiness_approval,
            readiness_confirmation_phrase=CONFIRMATION_PHRASE,
            readiness_audit_archive=readiness_audit_archive,
        )

    @app.route("/readiness/manual-approval", methods=["POST"])
    @roles_required("admin")
    def readiness_manual_approval():
        try:
            readiness = load_enforcement_readiness()
            history = load_readiness_history_summary()
            decision = evaluate_readiness_decision(readiness, history.entries)
            approval = record_manual_readiness_approval(
                decision,
                reviewer=request.form.get("reviewer", ""),
                confirmation=request.form.get("confirmation", ""),
                note=request.form.get("note", ""),
            )
            archive_manual_readiness_approval(decision, approval)
        except ValueError as exc:
            flash(translate_dynamic_text(exc), "danger")
        except Exception:
            flash(translate("readiness_record_failed"), "danger")
        else:
            log_event(
                "readiness-manual-approval",
                decision.status,
                "recorded; enforcement remains disabled",
            )
            flash(translate("readiness_recorded"), "success")
        return redirect(url_for("dashboard"))

    @app.route("/intelligence")
    @roles_required("admin", "editor", "viewer")
    def intelligence_report_page() -> str:
        rows = load_database()
        intelligence = build_intelligence_summary()
        diagnostics = build_intelligence_diagnostics()

        approved = sum(
            1
            for row in rows
            if (row.get("Status") or "Approved") == "Approved"
        )
        pending = sum(
            1
            for row in rows
            if (row.get("Status") or "Approved") != "Approved"
        )

        return render_template(
            "intelligence.html",
            intelligence=intelligence,
            diagnostics=diagnostics,
            domain_count=len(rows),
            approved=approved,
            pending=pending,
            version=read_version(),
        )

    @app.route("/domains")
    @roles_required("admin", "editor", "viewer")
    def domains() -> str:
        query = request.args.get("q", "").strip().lower()
        vendor = request.args.get("vendor", "").strip()
        category = request.args.get("category", "").strip()
        filter_name = request.args.get("filter", "").strip()
        status = request.args.get("status", "").strip()

        rows = load_database()
        if query:
            rows = [
                row for row in rows
                if query in row.get("Domain", "").lower()
                or query in row.get("Vendor", "").lower()
                or query in row.get("Category", "").lower()
                or query in row.get("Filter", "").lower()
            ]
        if vendor:
            rows = [row for row in rows if row.get("Vendor", "") == vendor]
        if category:
            rows = [row for row in rows if row.get("Category", "") == category]
        if filter_name:
            rows = [row for row in rows if row.get("Filter", "") == filter_name]
        if status:
            rows = [row for row in rows if (row.get("Status") or "Approved") == status]

        return render_template(
            "domains.html",
            rows=rows,
            query=query,
            q=request.args.get("q", ""),
            vendor=vendor,
            category=category,
            filter=filter_name,
            filter_name=filter_name,
            status=status,
            **database_options(),
        )

    @app.route("/domains/add", methods=["GET", "POST"])
    @roles_required("admin", "editor")
    def add_domain_page() -> str:
        if request.method == "POST":
            create_backup("web-add-domain")
            import scripts.services.suggestions_service as svc
            suggestions_snapshot = svc.SUGGESTIONS_CSV.read_text(encoding="utf-8") if svc.SUGGESTIONS_CSV.exists() else ""

            ok, errors = add_validated_domain(
                domain=request.form.get("domain", ""),
                vendor=request.form.get("vendor", ""),
                category=request.form.get("category", ""),
                filter_name=request.form.get("filter", ""),
                confidence=int(request.form.get("confidence") or 0),
                status=request.form.get("status", "Approved"),
                source="web-ui",
            )
            if ok:
                log_event("domain.add", request.form.get("domain", ""), "ok")
                flash(translate("domain_added_success"), "success")
                return redirect(url_for("domains"))
            for error in errors:
                flash(translate_dynamic_text(error), "danger")
        return render_template("domain_form.html", mode="add", row={}, **database_options())

    @app.route("/domains/<path:domain>/edit", methods=["GET", "POST"])
    @roles_required("admin", "editor")
    def edit_domain(domain: str) -> str:
        row = search_domain(domain)
        if not row:
            flash(translate("domain_not_found"), "danger")
            return redirect(url_for("domains"))
        if request.method == "POST":
            create_backup("web-edit-domain")
            ok, errors = update_validated_domain(
                domain=domain,
                vendor=request.form.get("vendor", ""),
                category=request.form.get("category", ""),
                filter_name=request.form.get("filter", ""),
                confidence=int(request.form.get("confidence") or 0),
            )
            if ok:
                log_event("domain.update", domain, "ok")
                flash(translate("domain_updated_success"), "success")
                return redirect(url_for("domains"))
            for error in errors:
                flash(translate_dynamic_text(error), "danger")
        return render_template("domain_form.html", mode="edit", row=row, **database_options())

    @app.route("/domains/<path:domain>/delete", methods=["POST"])
    @roles_required("admin")
    def delete_domain(domain: str) -> Any:
        create_backup("web-delete-domain")
        if remove_domain(domain):
            log_event("domain.delete", domain, "ok")
            flash(translate("domain_removed_success"), "success")
        else:
            flash(translate("domain_not_found"), "danger")
        return redirect(url_for("domains"))

    @app.route("/actions/<action>", methods=["POST"])
    @roles_required("admin", "editor")
    def action(action: str) -> str:
        allowed = {"doctor", "validate", "build", "intelligence-check", "intelligence-report"}
        if action not in allowed:
            flash(translate("invalid_action"), "danger")
            return redirect(url_for("dashboard"))
        if action == "build" and not (app.testing and not app.config.get("SECURITY_TESTING")) and not current_user.has_role("admin"):
            return (translate("forbidden"), 403)
        if action == "build":
            create_backup("web-build")
        started = time.perf_counter()
        code, output = run_fivebr(action)
        duration_ms = round((time.perf_counter() - started) * 1000)
        log_event(f"action.{action}", action, "ok" if code == 0 else "error", output[:500])
        operation_key = audit_operation_key(action)
        return render_template(
            "output.html", title=translate(f"operation_{operation_key}"),
            operation=operation_key, code=code, output=output,
            executed_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            duration_ms=duration_ms,
        )

    @app.route("/analyze", methods=["GET", "POST"])
    @roles_required("admin", "editor")
    def analyze() -> str:
        output = ""
        code = 0
        domain = request.args.get("domain", "").strip()
        if request.method == "POST":
            domain = request.form.get("domain", "").strip()
            if not domain:
                flash(translate("domain_required"), "danger")
            else:
                code, output = run_fivebr("analyze", domain)
        return render_template("analyze.html", output=output, code=code, domain=domain)

    @app.route("/analyze-log", methods=["GET", "POST"])
    @roles_required("admin", "editor")
    def analyze_log() -> str:
        output = ""
        code = 0
        if request.method == "POST":
            min_seen = request.form.get("min_seen", "10") or "10"
            limit = request.form.get("limit", "100") or "100"
            file = request.files.get("querylog")
            path = request.form.get("path", "").strip()
            if file and file.filename:
                safe_name = Path(file.filename).name
                path_obj = UPLOADS_DIR / safe_name
                file.save(path_obj)
                path = str(path_obj)
            if not path:
                flash(translate("querylog_required"), "danger")
            else:
                create_backup("web-analyze-log")
                code, output = run_fivebr("analyze-log", path, "--min-seen", min_seen, "--limit", limit)
                log_event("analyze-log", path, "ok" if code == 0 else "error", f"min_seen={min_seen}; limit={limit}")
        return render_template("analyze_log.html", output=output, code=code)


    @app.route("/analysis")
    @roles_required("admin", "editor", "viewer")
    def analysis() -> str:
        all_rows = load_suggestions()
        filtered_rows = filter_suggestion_rows(all_rows, request.args)
        limit = to_int(request.args.get("limit"), 100)
        if limit <= 0:
            limit = 100
        rows = filtered_rows[:limit]
        opts = suggestion_options(all_rows)
        return render_template(
            "analysis.html",
            rows=rows,
            total_rows=len(all_rows),
            filtered_count=len(filtered_rows),
            stats=suggestion_analysis(all_rows),
            filtered_stats=suggestion_analysis(filtered_rows),
            q=request.args.get("q", ""),
            vendor=request.args.get("vendor", ""),
            category=request.args.get("category", ""),
            filter_name=request.args.get("filter", ""),
            recommendation=request.args.get("recommendation", ""),
            min_confidence=request.args.get("min_confidence", ""),
            sort=request.args.get("sort", "seen"),
            direction_value=request.args.get("direction", "desc"),
            limit=limit,
            **opts,
        )


    @app.route("/review-queue")
    @roles_required("admin", "editor", "viewer")
    def review_queue() -> str:
        include_decided = request.args.get("include_decided") == "1"
        all_rows = load_review_queue(include_decided=include_decided)
        filtered_rows = filter_review_queue_rows(all_rows, request.args)
        limit = to_int(request.args.get("limit"), 100)
        if limit <= 0:
            limit = 100
        opts = suggestion_options(all_rows)
        return render_template(
            "review_queue.html",
            rows=filtered_rows[:limit],
            total_rows=len(all_rows),
            filtered_count=len(filtered_rows),
            stats=review_queue_stats(all_rows),
            q=request.args.get("q", ""),
            vendor=request.args.get("vendor", ""),
            category=request.args.get("category", ""),
            recommendation=request.args.get("recommendation", ""),
            status=request.args.get("status", ""),
            min_confidence=request.args.get("min_confidence", ""),
            sort=request.args.get("sort", "seen"),
            include_decided=include_decided,
            limit=limit,
            **opts,
        )

    @app.route("/review-queue/<path:domain>/<action>", methods=["POST"])
    @roles_required("admin")
    def review_queue_action(domain: str, action: str):
        allowed = {"approved", "rejected", "ignored"}
        if action not in allowed:
            flash(translate("invalid_review_action"), "danger")
            return redirect(url_for("review_queue"))

        suggestion = find_suggestion(domain)
        if not suggestion:
            flash(translate("suggestion_not_found"), "danger")
            return redirect(url_for("review_queue"))

        reason = request.form.get("reason", "").strip()

        test_confirmed = (
            request.form.get(
                "test_confirmed"
            )
            == "on"
        )

        override_confirmed = (
            request.form.get(
                "override_confirmed"
            )
            == "on"
        )

        manual_review_confirmed = (
            request.form.get(
                "manual_review_confirmed"
            )
            == "on"
        )

        guardrail_evidence = {
            "test_confirmed": test_confirmed,
            "override_confirmed": (
                override_confirmed
            ),
            "manual_review_confirmed": (
                manual_review_confirmed
            ),
        }

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
                    flash(translate_dynamic_text(error), "danger")
                append_decision(
                    suggestion,
                    "approved-failed",
                    "; ".join(errors) or reason,
                    **guardrail_evidence,
                )
                log_event("review_queue.approved", domain, "error", "; ".join(errors))
                return redirect(request.form.get("next") or url_for("review_queue"))

            # IMPORTANT: use module-level run_fivebr so pytest monkeypatching web.app.run_fivebr works.
            code, output = globals()["run_fivebr"]("build")

            if code != 0:
                append_decision(
                    suggestion,
                    "approved-build-failed",
                    output or reason,
                    **guardrail_evidence,
                )
                log_event("review_queue.build", domain, "error", output)
                flash(translate("domain_added_build_failed"), "danger")
                return redirect(request.form.get("next") or url_for("review_queue"))

            remove_suggestion(domain)
            append_decision(
                suggestion,
                action,
                reason,
                **guardrail_evidence,
            )
            log_event("review_queue.approved", domain, "ok", output)
            flash(translate("suggestion_approved_rebuilt"), "success")
            return redirect(request.form.get("next") or url_for("review_queue"))

        # Review-only actions are intentionally non-destructive.
        append_decision(
                suggestion,
                action,
                reason,
                **guardrail_evidence,
            )
        log_event(f"review_queue.{action}", domain, "ok", reason)
        flash(translate("review_saved"), "success")
        return redirect(request.form.get("next") or url_for("review_queue"))

    @app.route("/reports/suggestions")
    @roles_required("admin", "editor", "viewer")
    def suggestions() -> str:
        rows = load_suggestions()
        return render_template("suggestions.html", rows=rows)

    @app.route("/reports/suggestions.md")
    @roles_required("admin", "editor", "viewer")
    def suggestions_markdown() -> str:
        path = REPORTS_DIR / "suggestions.md"
        text = path.read_text(encoding="utf-8") if path.exists() else translate("no_suggestions_report")
        return render_template("markdown.html", title=translate("suggestions_markdown"), text=text)

    @app.route("/suggestions/<path:domain>/approve", methods=["GET", "POST"])
    @roles_required("admin")
    def approve_suggestion(domain: str):
        suggestion = find_suggestion(domain)
        if not suggestion:
            flash(translate("suggestion_not_found"), "danger")
            return redirect(url_for("suggestions"))
        if request.method == "POST":
            create_backup("web-approve-suggestion")
            ok, errors = add_validated_domain(
                domain=request.form.get("domain", suggestion.get("Domain", "")),
                vendor=request.form.get("vendor", suggestion.get("Suggested Vendor", "")),
                category=request.form.get("category", suggestion.get("Suggested Category", "")),
                filter_name=request.form.get("filter", suggestion.get("Suggested Filter", "")),
                confidence=int(request.form.get("confidence") or suggestion.get("Confidence") or 0),
                status="Approved",
                source="analyze-log",
                evidence=f"Seen {suggestion.get('Seen', '')} times; {suggestion.get('Reasons', '')}",
                notes="Approved from Web UI suggestions",
            )
            if ok:
                remove_suggestion(domain)
                log_event("suggestion.approve", domain, "ok")
                flash(translate("suggestion_approved"), "success")
                return redirect(url_for("suggestions"))
            for error in errors:
                flash(translate_dynamic_text(error), "danger")
        return render_template("suggestion_form.html", row=suggestion, suggestion=suggestion, **database_options())

    @app.route("/suggestions/<path:domain>/reject", methods=["POST"])
    @roles_required("admin", "editor")
    def reject_suggestion(domain: str):
        suggestion = find_suggestion(domain)
        if not suggestion:
            flash(translate("suggestion_not_found"), "danger")
            return redirect(url_for("suggestions"))
        create_backup("web-reject-suggestion")
        append_rejected(suggestion, request.form.get("reason", "Rejected from Web UI"))
        remove_suggestion(domain)
        log_event("suggestion.reject", domain, "ok")
        flash(translate("suggestion_rejected"), "success")
        return redirect(url_for("suggestions"))

    @app.route("/releases")
    @roles_required("admin", "editor", "viewer")
    def releases() -> str:
        return render_template("releases.html", files=release_rows())

    @app.route("/audit")
    @roles_required("admin", "editor", "viewer")
    def audit_log() -> str:
        return render_template("audit.html", events=recent_events(100))

    @app.route("/releases/<path:filename>")
    @roles_required("admin", "editor", "viewer")
    def download_release(filename: str):
        return send_from_directory(RELEASES_DIR, filename, as_attachment=False)

    app.jinja_env.globals.update(
        current_user=current_user,
        normalize_unknown=normalize_unknown,
        confidence_level=confidence_level,
        recommendation_badge=recommendation_badge,
        explain_suggestion=explain_suggestion,
        translate_status=translate_status,
        translate_category=translate_category,
        translate_vendor=translate_vendor,
        translate_recommendation=translate_recommendation,
        translate_guardrail=translate_guardrail,
        translate_confidence=translate_confidence,
        translate_decision=translate_decision,
        translate_dynamic_text=translate_dynamic_text,
        audit_operation_key=audit_operation_key,
        format_display_datetime=format_display_datetime,
    )

    return app


app = create_app()


def main() -> int:
    app.run(host="0.0.0.0", port=8089)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# v1.6.4 helper for one-click approval tests
def run_fivebr(*args):
    import subprocess
    proc = subprocess.run(
        ["fivebr", *args],
        cwd=BASE_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def restore_suggestion_if_missing(suggestion):
    import csv
    import scripts.services.suggestions_service as svc

    fieldnames = [
        "Domain", "Seen", "Root", "Suggested Vendor",
        "Suggested Category", "Suggested Filter",
        "Confidence", "Recommendation", "Reasons",
    ]
    domain = (suggestion.get("Domain", "") or "").strip()
    if not domain:
        return

    path = svc.SUGGESTIONS_CSV
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if domain in text:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not text:
            writer.writeheader()
        writer.writerow({key: suggestion.get(key, "") for key in fieldnames})
