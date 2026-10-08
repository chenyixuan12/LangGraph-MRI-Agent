def test_health_shape():
    # Lightweight contract test that does not require a running server.
    from app.api.routes.health import health
    assert health()["status"] == "ok"
