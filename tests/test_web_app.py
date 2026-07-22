import pytest

flask = pytest.importorskip("flask")

from web.app import create_app


def test_web_dashboard_loads():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"5ibr" in response.data
