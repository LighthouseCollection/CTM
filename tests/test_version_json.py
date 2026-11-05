"""D-0023: /version.json shows four public facts only."""

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FACTS = {"name", "version", "plenix_version", "build_time"}


def test_version_json_returns_exactly_four_public_facts(client, settings, tmp_path):
    (tmp_path / "BUILD_TIME").write_text("2026-11-04T10:00:00Z\n")
    settings.CTM_BUILD_INFO_DIR = tmp_path

    response = client.get("/version.json")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert response.json() == {
        "name": "CTM 3.0",
        "version": project["project"]["version"],
        "plenix_version": settings.PLENIX_BASE.rstrip("/").rsplit("/", 1)[-1],
        "build_time": "2026-11-04T10:00:00Z",
    }


def test_version_json_reads_version_from_the_build_copy(client, settings, tmp_path):
    # The image has no pyproject.toml; the Dockerfile copies it into the build dir.
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "ctm"\nversion = "9.9.9"\n')
    settings.CTM_BUILD_INFO_DIR = tmp_path

    data = client.get("/version.json").json()

    assert set(data) == FACTS
    assert data["version"] == "9.9.9"


def test_version_json_reports_unknown_build_time_honestly(client, settings, tmp_path):
    settings.CTM_BUILD_INFO_DIR = tmp_path  # no BUILD_TIME file

    data = client.get("/version.json").json()

    assert set(data) == FACTS
    assert data["build_time"] is None


def test_version_json_is_read_only(client):
    assert client.post("/version.json").status_code == 405
