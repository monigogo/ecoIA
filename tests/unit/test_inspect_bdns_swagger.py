from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.inspect_bdns_swagger import (
    DEFAULT_FIXTURE,
    main,
    render_snapshot,
    summarize_paths,
)


def test_default_fixture_exists_and_is_valid_openapi() -> None:
    assert DEFAULT_FIXTURE.is_file()
    document = json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    assert document.get("openapi", "").startswith("3.")
    assert isinstance(document.get("paths"), dict)


def test_summarize_paths_flags_convocatoria_endpoints() -> None:
    document = json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    summaries = summarize_paths(document)
    paths = {item.path for item in summaries}
    assert "/convocatorias/busqueda" in paths
    assert "/health" in paths

    candidates = [item for item in summaries if item.looks_like_convocatorias_search]
    candidate_paths = {item.path for item in candidates}
    assert "/convocatorias/busqueda" in candidate_paths
    assert "/health" not in candidate_paths


def test_render_snapshot_contains_table_and_candidates() -> None:
    document = json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    summaries = summarize_paths(document)
    snapshot = render_snapshot(summaries, source_label="fixture")

    assert "# BDNS OpenAPI snapshot" in snapshot
    assert "| Path | Methods | Summary |" in snapshot
    assert "/convocatorias/busqueda" in snapshot
    assert "Candidate search endpoints" in snapshot


def test_main_writes_snapshot_to_requested_path() -> None:
    snapshot_path = Path(".test_artifacts/inspect_bdns_swagger/snapshot.md")
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    exit_code = main(
        [
            "--source",
            str(DEFAULT_FIXTURE),
            "--snapshot",
            str(snapshot_path),
        ]
    )
    assert exit_code == 0
    text = snapshot_path.read_text(encoding="utf-8")
    assert "/convocatorias/busqueda" in text
    assert "Candidate search endpoints" in text


def test_bdns_service_path_is_present_in_fixture_swagger() -> None:
    """Regression guard: the path BDNSService hits must exist in the
    bundled BDNS swagger fixture. If BDNS changes the path, update both
    the fixture and the service together."""

    from app.services import bdns_service

    document = json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    paths = set(document.get("paths", {}).keys())
    assert bdns_service._CONVOCATORIAS_PATH in paths


def test_main_raises_when_source_missing() -> None:
    missing = Path(".test_artifacts/inspect_bdns_swagger/does_not_exist.json")
    with pytest.raises(SystemExit, match="not found"):
        main(["--source", str(missing)])
