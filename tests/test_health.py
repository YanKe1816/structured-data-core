import asyncio

from app.main import app


def req(method: str, url: str, body: bytes = b""):
    return asyncio.run(app.dispatch(method, url, body))


def test_required_routes_exist_and_health_ok():
    assert req("GET", "/health").status_code == 200
    assert req("GET", "/health").json() == {"status": "ok"}
    assert req("GET", "/privacy").status_code == 200
    assert req("GET", "/terms").status_code == 200
    assert req("GET", "/support").status_code == 200
    assert req("GET", "/.well-known/openai-apps-challenge").status_code == 200
    manifest = req("GET", "/mcp")
    assert manifest.status_code == 200
    assert manifest.json()["name"] == "structured-data-core"
