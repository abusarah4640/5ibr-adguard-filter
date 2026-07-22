import csv

from web.app import app


def test_review_queue_approve_adds_domain_builds_and_removes_suggestion(tmp_path, monkeypatch):
    import scripts.database as db
    import scripts.services.database_service as database_service
    import scripts.services.suggestions_service as svc
    import web.app as webapp

    database = tmp_path / 'domains.csv'
    suggestions = tmp_path / 'suggestions.csv'
    decisions = tmp_path / 'suggestion-decisions.csv'

    database.write_text(
        'Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes,Evidence,Created,Updated,Reviewer\n',
        encoding='utf-8',
    )
    suggestions.write_text(
        'Domain,Seen,Root,Suggested Vendor,Suggested Category,Suggested Filter,Confidence,Recommendation,Reasons\n'
        'approve.test,9,approve.test,Example,Telemetry,telemetry,75,review,matched test\n',
        encoding='utf-8',
    )

    monkeypatch.setattr(db, 'DATABASE', database)
    monkeypatch.setattr(database_service, 'DATABASE', database, raising=False)
    monkeypatch.setattr(svc, 'SUGGESTIONS_CSV', suggestions)
    monkeypatch.setattr(svc, 'DECISIONS_CSV', decisions)
    monkeypatch.setattr(webapp, 'create_backup', lambda reason: tmp_path)
    monkeypatch.setattr(webapp, 'run_fivebr', lambda *args: (0, 'Build completed successfully.'))

    app.testing = True
    client = app.test_client()
    response = client.post('/review-queue/approve.test/approved', data={'reason': 'approve from test'})

    assert response.status_code in {302, 303}

    with database.open('r', newline='', encoding='utf-8') as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert rows[0]['Domain'] == 'approve.test'
    assert rows[0]['Status'] == 'Approved'
    assert rows[0]['Source'] == 'review-queue'

    remaining = suggestions.read_text(encoding='utf-8')
    assert 'approve.test' not in remaining
    assert decisions.exists()
    assert 'approved' in decisions.read_text(encoding='utf-8')


def test_review_queue_approve_build_failure_keeps_suggestion(tmp_path, monkeypatch):
    import scripts.database as db
    import scripts.services.database_service as database_service
    import scripts.services.suggestions_service as svc
    import web.app as webapp

    database = tmp_path / 'domains.csv'
    suggestions = tmp_path / 'suggestions.csv'
    decisions = tmp_path / 'suggestion-decisions.csv'

    database.write_text(
        'Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes,Evidence,Created,Updated,Reviewer\n',
        encoding='utf-8',
    )
    suggestions.write_text(
        'Domain,Seen,Root,Suggested Vendor,Suggested Category,Suggested Filter,Confidence,Recommendation,Reasons\n'
        'buildfail.test,9,buildfail.test,Example,Telemetry,telemetry,75,review,matched test\n',
        encoding='utf-8',
    )

    monkeypatch.setattr(db, 'DATABASE', database)
    monkeypatch.setattr(database_service, 'DATABASE', database, raising=False)
    monkeypatch.setattr(svc, 'SUGGESTIONS_CSV', suggestions)
    monkeypatch.setattr(svc, 'DECISIONS_CSV', decisions)
    monkeypatch.setattr(webapp, 'create_backup', lambda reason: tmp_path)
    monkeypatch.setattr(webapp, 'run_fivebr', lambda *args: (1, 'build failed'))

    app.testing = True
    client = app.test_client()
    response = client.post('/review-queue/buildfail.test/approved')

    assert response.status_code in {302, 303}
    assert 'buildfail.test' in suggestions.read_text(encoding='utf-8')
    assert 'buildfail.test' not in database.read_text(encoding='utf-8')
    assert decisions.exists()
    assert 'approved-build-failed' in decisions.read_text(encoding='utf-8')
    assert 'approved-build-rollback-failed' not in decisions.read_text(
        encoding='utf-8'
    )


def test_review_queue_records_failed_automatic_rollback(
    tmp_path,
    monkeypatch,
):
    import scripts.database as db
    import scripts.services.database_service as database_service
    import scripts.services.suggestions_service as svc
    import web.app as webapp

    database = tmp_path / "domains.csv"
    suggestions = tmp_path / "suggestions.csv"
    decisions = tmp_path / "suggestion-decisions.csv"

    database.write_text(
        "Domain,Vendor,Category,Filter,Confidence,Status,Source,"
        "Notes,Evidence,Created,Updated,Reviewer\n",
        encoding="utf-8",
    )
    suggestions.write_text(
        "Domain,Seen,Root,Suggested Vendor,Suggested Category,"
        "Suggested Filter,Confidence,Recommendation,Reasons\n"
        "rollbackfail.test,9,rollbackfail.test,Example,Telemetry,"
        "telemetry,75,review,matched test\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(db, "DATABASE", database)
    monkeypatch.setattr(
        database_service,
        "DATABASE",
        database,
        raising=False,
    )
    monkeypatch.setattr(svc, "SUGGESTIONS_CSV", suggestions)
    monkeypatch.setattr(svc, "DECISIONS_CSV", decisions)
    monkeypatch.setattr(webapp, "create_backup", lambda reason: tmp_path)
    monkeypatch.setattr(
        webapp,
        "run_fivebr",
        lambda *args: (1, "build failed"),
    )
    monkeypatch.setattr(webapp, "remove_domain", lambda domain: False)

    app.testing = True
    client = app.test_client()
    response = client.post(
        "/review-queue/rollbackfail.test/approved"
    )

    assert response.status_code in {302, 303}
    assert decisions.exists()
    decision_text = decisions.read_text(encoding="utf-8")
    assert "approved-build-rollback-failed" in decision_text
    assert "automatic database rollback failed" in decision_text
