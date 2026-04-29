from __future__ import annotations

import uuid
from pathlib import Path

import pytest


@pytest.fixture
def smoke_tmp_path() -> Path:
    root = Path(".pytest_tmp_smoke")
    root.mkdir(exist_ok=True)
    path = root / str(uuid.uuid4())
    path.mkdir()
    return path
