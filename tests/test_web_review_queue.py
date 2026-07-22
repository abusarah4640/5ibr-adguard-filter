from pathlib import Path

from web.app import app
from scripts.services.suggestions_service import load_review_queue


def test_review_queue_page_loads():
    client = app.test_client()
    response = client.get('/review-queue')
    assert response.status_code == 200
    assert b'Review Queue' in response.data or 'قائمة المراجعة'.encode() in response.data


def test_review_queue_action_records_decision(tmp_path, monkeypatch):
    import scripts.services.suggestions_service as svc
    import web.app as webapp

    suggestions = tmp_path / 'suggestions.csv'
    decisions = tmp_path / 'suggestion-decisions.csv'
    suggestions.write_text(
        'Domain,Seen,Root,Suggested Vendor,Suggested Category,Suggested Filter,Confidence,Recommendation,Reasons\n'
        'example.test,5,example.test,Example,Telemetry,telemetry,65,review,matched test\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(svc, 'SUGGESTIONS_CSV', suggestions)
    monkeypatch.setattr(svc, 'DECISIONS_CSV', decisions)
    monkeypatch.setattr(webapp, 'create_backup', lambda reason: tmp_path)

    webapp.app.testing = True
    client = webapp.app.test_client()
    response = client.post('/review-queue/example.test/ignored', data={'reason': 'test ignore'})

    assert response.status_code in {302, 303}
    assert decisions.exists()
    rows = load_review_queue(include_decided=True)
    assert rows[0]['Review Status'] == 'ignored'
    assert rows[0]['Review Reason'] == 'test ignore'
