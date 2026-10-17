import solfa.render_verovio
import pytest


@pytest.fixture
def capture(monkeypatch):
    captured = []
    monkeypatch.setattr(solfa.render_verovio, 'show', captured.append)
    return captured
