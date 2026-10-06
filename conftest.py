import complib.render
import pytest


@pytest.fixture
def capture(monkeypatch):
    captured = []
    monkeypatch.setattr(complib.render, 'show', captured.append)
    return captured
