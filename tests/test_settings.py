from astropost import settings


def test_no_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ENV_PATH", tmp_path / "missing.env")
    monkeypatch.delenv("ASTROPOST_FROM", raising=False)
    monkeypatch.delenv("ASTROPOST_ALWAYS_CC", raising=False)
    assert settings.default_from() is None
    assert settings.with_always_cc(["a@x.org"]) == ["a@x.org"]


def test_env_values(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ENV_PATH", tmp_path / "missing.env")
    monkeypatch.setenv("ASTROPOST_FROM", "Ada <ada@example.org>")
    monkeypatch.setenv("ASTROPOST_ALWAYS_CC", "me@example.org, a@x.org")
    assert settings.default_from() == "Ada <ada@example.org>"
    assert settings.with_always_cc(["a@x.org"]) == ["a@x.org", "me@example.org"]
