import complib.render_verovio
import pytest


@pytest.fixture
def capture(monkeypatch):
    captured = []
    monkeypatch.setattr(complib.render_verovio, 'show', captured.append)
    return captured
