import musicat.render_verovio
import pytest


@pytest.fixture
def capture(monkeypatch):
    captured = []
    monkeypatch.setattr(musicat.render_verovio, 'show', captured.append)
    return captured
