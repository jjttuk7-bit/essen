import app.main as main


def test_run_uses_configured_host_and_port(monkeypatch):
    monkeypatch.setenv("HUMAN_LAYER_HOST", "0.0.0.0")
    monkeypatch.setenv("HUMAN_LAYER_PORT", "9000")
    called: dict[str, object] = {}

    monkeypatch.setattr(
        main.uvicorn,
        "run",
        lambda app, host, port: called.update(app=app, host=host, port=port),
    )

    main.run()

    assert called == {"app": main.app, "host": "0.0.0.0", "port": 9000}
