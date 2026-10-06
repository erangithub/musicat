import complib
import pytest


@pytest.fixture
def capture(monkeypatch):
    captured = []
    monkeypatch.setattr(complib, 'show', captured.append)
    return captured
