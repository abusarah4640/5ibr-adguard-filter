import pytest

flask = pytest.importorskip("flask")

from web.app import create_app


def test_analysis_dashboard_loads():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    response = client.get("/analysis")
    assert response.status_code == 200
    assert b"Analysis" in response.data or "التحليل".encode() in response.data


def test_analysis_dashboard_filters():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    response = client.get("/analysis?recommendation=review&min_confidence=40&sort=confidence")
    assert response.status_code == 200
